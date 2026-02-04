"""Database MCP Server - SQLite database access for inventory management.

This module provides a Model Context Protocol server for database operations,
enabling agents to query and update inventory data stored in SQLite.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from datetime import datetime

from protocols.mcp.base_server import (
    BaseMCPServer,
    MCPError,
    MCPErrorCode,
)

logger = logging.getLogger(__name__)


class DatabaseMCPServer(BaseMCPServer):
    """MCP Server for SQLite database operations.

    Provides tools for querying and updating inventory data in a SQLite database.
    Supports connection pooling and transaction management.

    Attributes:
        db_path: Path to the SQLite database file
        connection: Active database connection (if pooling disabled)
    """

    def __init__(
        self,
        db_path: str = "data/inventory.db",
        create_tables: bool = True
    ):
        """Initialize the Database MCP Server.

        Args:
            db_path: Path to SQLite database file
            create_tables: Whether to create tables if they don't exist
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize the database if needed
        if create_tables:
            self._initialize_database()

        # Initialize base server
        super().__init__(
            server_id="database_mcp",
            name="Database MCP Server",
            version="1.0.0"
        )

    def _get_description(self) -> str:
        """Get server description."""
        return "SQLite database server for inventory management"

    def _register_tools(self) -> None:
        """Register database tools."""

        self.register_tool(
            name="query_inventory",
            handler=self._query_inventory,
            description="Query inventory items with optional filters",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Filter by product ID"},
                    "below_reorder_point": {"type": "boolean", "description": "Only items below reorder point"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "limit": {"type": "integer", "description": "Maximum results to return"}
                }
            },
            output_schema={
                "type": "array",
                "items": {"type": "object"}
            }
        )

        self.register_tool(
            name="update_stock",
            handler=self._update_stock,
            description="Update stock quantity for a product",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID to update"},
                    "quantity_change": {"type": "integer", "description": "Change in quantity (positive or negative)"},
                    "reason": {"type": "string", "description": "Reason for the update"}
                },
                "required": ["product_id", "quantity_change"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "new_quantity": {"type": "integer"}
                }
            }
        )

        self.register_tool(
            name="get_inventory_summary",
            handler=self._get_inventory_summary,
            description="Get summary statistics for inventory",
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {
                    "total_items": {"type": "integer"},
                    "total_value": {"type": "number"},
                    "low_stock_count": {"type": "integer"}
                }
            }
        )

        self.register_tool(
            name="record_po_transaction",
            handler=self._record_po_transaction,
            description="Record a purchase order transaction",
            input_schema={
                "type": "object",
                "properties": {
                    "po_number": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "unit_price": {"type": "number"},
                    "supplier_id": {"type": "string"}
                },
                "required": ["po_number", "product_id", "quantity", "unit_price"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "integer"},
                    "success": {"type": "boolean"}
                }
            }
        )

        self.register_tool(
            name="get_transaction_history",
            handler=self._get_transaction_history,
            description="Get transaction history for a product or PO",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "po_number": {"type": "string"},
                    "limit": {"type": "integer", "default": 50}
                }
            },
            output_schema={
                "type": "array",
                "items": {"type": "object"}
            }
        )

    @contextmanager
    def _get_connection(self):
        """Get a database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create inventory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    product_id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    current_stock INTEGER NOT NULL DEFAULT 0,
                    reorder_point INTEGER NOT NULL DEFAULT 10,
                    reorder_quantity INTEGER NOT NULL DEFAULT 50,
                    unit_price REAL NOT NULL DEFAULT 0,
                    category TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    po_number TEXT,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    supplier_id TEXT,
                    transaction_type TEXT DEFAULT 'purchase',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES inventory(product_id)
                )
            """)

            # Create stock_changes table for audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    old_quantity INTEGER NOT NULL,
                    new_quantity INTEGER NOT NULL,
                    change_amount INTEGER NOT NULL,
                    reason TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES inventory(product_id)
                )
            """)

            logger.info(f"Database initialized at {self.db_path}")

    def _query_inventory(
        self,
        product_id: Optional[str] = None,
        below_reorder_point: bool = False,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query inventory items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM inventory WHERE 1=1"
            params = []

            if product_id:
                query += " AND product_id = ?"
                params.append(product_id)

            if below_reorder_point:
                query += " AND current_stock < reorder_point"

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY product_id LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def _update_stock(
        self,
        product_id: str,
        quantity_change: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update stock quantity for a product."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get current stock
            cursor.execute(
                "SELECT current_stock FROM inventory WHERE product_id = ?",
                (product_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise MCPError(
                    MCPErrorCode.RESOURCE_NOT_FOUND,
                    f"Product not found: {product_id}"
                )

            old_quantity = row["current_stock"]
            new_quantity = old_quantity + quantity_change

            if new_quantity < 0:
                raise MCPError(
                    MCPErrorCode.INVALID_PARAMS,
                    f"Cannot reduce stock below 0. Current: {old_quantity}, Change: {quantity_change}"
                )

            # Update inventory
            cursor.execute(
                """UPDATE inventory
                   SET current_stock = ?, last_updated = CURRENT_TIMESTAMP
                   WHERE product_id = ?""",
                (new_quantity, product_id)
            )

            # Record change in audit log
            cursor.execute(
                """INSERT INTO stock_changes
                   (product_id, old_quantity, new_quantity, change_amount, reason)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, old_quantity, new_quantity, quantity_change, reason)
            )

            logger.info(
                f"Stock updated for {product_id}: {old_quantity} -> {new_quantity} ({quantity_change:+d})"
            )

            return {
                "success": True,
                "product_id": product_id,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
                "change": quantity_change
            }

    def _get_inventory_summary(self) -> Dict[str, Any]:
        """Get inventory summary statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total items and value
            cursor.execute("""
                SELECT
                    COUNT(*) as total_items,
                    SUM(current_stock) as total_units,
                    SUM(current_stock * unit_price) as total_value
                FROM inventory
            """)
            totals = dict(cursor.fetchone())

            # Low stock count
            cursor.execute("""
                SELECT COUNT(*) as low_stock_count
                FROM inventory
                WHERE current_stock < reorder_point
            """)
            low_stock = dict(cursor.fetchone())

            # Out of stock count
            cursor.execute("""
                SELECT COUNT(*) as out_of_stock_count
                FROM inventory
                WHERE current_stock = 0
            """)
            out_of_stock = dict(cursor.fetchone())

            return {
                "total_items": totals["total_items"] or 0,
                "total_units": totals["total_units"] or 0,
                "total_value": totals["total_value"] or 0.0,
                "low_stock_count": low_stock["low_stock_count"] or 0,
                "out_of_stock_count": out_of_stock["out_of_stock_count"] or 0
            }

    def _record_po_transaction(
        self,
        po_number: str,
        product_id: str,
        quantity: int,
        unit_price: float,
        supplier_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a purchase order transaction."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            total_amount = quantity * unit_price

            cursor.execute(
                """INSERT INTO transactions
                   (po_number, product_id, quantity, unit_price, total_amount, supplier_id, transaction_type)
                   VALUES (?, ?, ?, ?, ?, ?, 'purchase')""",
                (po_number, product_id, quantity, unit_price, total_amount, supplier_id)
            )

            transaction_id = cursor.lastrowid

            logger.info(
                f"Recorded PO transaction: {po_number}, {product_id}, qty={quantity}, total=${total_amount:.2f}"
            )

            return {
                "success": True,
                "transaction_id": transaction_id,
                "po_number": po_number,
                "total_amount": total_amount
            }

    def _get_transaction_history(
        self,
        product_id: Optional[str] = None,
        po_number: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get transaction history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM transactions WHERE 1=1"
            params = []

            if product_id:
                query += " AND product_id = ?"
                params.append(product_id)

            if po_number:
                query += " AND po_number = ?"
                params.append(po_number)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def import_from_csv(self, csv_path: str) -> Dict[str, Any]:
        """Import inventory data from CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Import summary
        """
        import csv

        imported = 0
        errors = []

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for row in reader:
                    try:
                        cursor.execute(
                            """INSERT OR REPLACE INTO inventory
                               (product_id, product_name, current_stock, reorder_point,
                                reorder_quantity, unit_price, category)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                row.get("product_id", row.get("item_id")),
                                row.get("product_name", row.get("item_name", "Unknown")),
                                int(row.get("current_stock", row.get("quantity", 0))),
                                int(row.get("reorder_point", 10)),
                                int(row.get("reorder_quantity", 50)),
                                float(row.get("unit_price", row.get("price", 0))),
                                row.get("category", "General")
                            )
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Row error: {e}")

        logger.info(f"Imported {imported} items from {csv_path}")

        return {
            "imported": imported,
            "errors": errors,
            "source": csv_path
        }
