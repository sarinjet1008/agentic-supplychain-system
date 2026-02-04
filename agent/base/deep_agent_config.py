"""Deep Agents SDK Configuration.

This module provides configuration and utilities for integrating
with the Deep Agents SDK, including model settings, tool configurations,
and memory management.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


class ToolCategory(str, Enum):
    """Categories of Deep Agents tools."""
    PLANNING = "planning"
    FILE_SYSTEM = "file_system"
    SUBAGENT = "subagent"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for LLM model.

    Attributes:
        provider: LLM provider (anthropic, openai, etc.)
        model_id: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        api_key_env: Environment variable for API key
    """
    provider: ModelProvider = ModelProvider.ANTHROPIC
    model_id: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key_env: str = "ANTHROPIC_API_KEY"

    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        return os.getenv(self.api_key_env)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider": self.provider.value,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ToolConfig:
    """Configuration for a Deep Agents tool.

    Attributes:
        name: Tool name
        category: Tool category
        enabled: Whether the tool is enabled
        settings: Tool-specific settings
    """
    name: str
    category: ToolCategory
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryConfig:
    """Configuration for agent memory.

    Attributes:
        enabled: Whether memory is enabled
        max_history: Maximum conversation history to keep
        persistence_enabled: Whether to persist to disk
        persistence_path: Path for persistence storage
    """
    enabled: bool = True
    max_history: int = 50
    persistence_enabled: bool = False
    persistence_path: str = "data/memory"


@dataclass
class SubAgentConfig:
    """Configuration for sub-agent spawning.

    Attributes:
        max_concurrent: Maximum concurrent sub-agents
        timeout_seconds: Timeout for sub-agent execution
        allowed_agents: List of allowed sub-agent types
    """
    max_concurrent: int = 5
    timeout_seconds: int = 300
    allowed_agents: List[str] = field(default_factory=lambda: [
        "purchase_order.validator",
        "inventory_monitor",
        "supplier_selector"
    ])


@dataclass
class DeepAgentConfig:
    """Main configuration for Deep Agents SDK integration.

    Attributes:
        model: Model configuration
        tools: List of tool configurations
        memory: Memory configuration
        subagent: Sub-agent configuration
        sandbox_enabled: Whether to run in sandbox mode
        logging_level: Logging level for Deep Agents
    """
    model: ModelConfig = field(default_factory=ModelConfig)
    tools: List[ToolConfig] = field(default_factory=list)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    subagent: SubAgentConfig = field(default_factory=SubAgentConfig)
    sandbox_enabled: bool = True
    logging_level: str = "INFO"

    def __post_init__(self):
        """Initialize default tools if none provided."""
        if not self.tools:
            self.tools = self._default_tools()

    def _default_tools(self) -> List[ToolConfig]:
        """Get default tool configurations."""
        return [
            ToolConfig(
                name="write_todos",
                category=ToolCategory.PLANNING,
                enabled=True,
                settings={"max_steps": 10}
            ),
            ToolConfig(
                name="read_file",
                category=ToolCategory.FILE_SYSTEM,
                enabled=True,
                settings={"max_size_bytes": 1_000_000}
            ),
            ToolConfig(
                name="write_file",
                category=ToolCategory.FILE_SYSTEM,
                enabled=True,
                settings={"allowed_extensions": [".json", ".csv", ".txt"]}
            ),
            ToolConfig(
                name="list_files",
                category=ToolCategory.FILE_SYSTEM,
                enabled=True,
                settings={"max_depth": 3}
            ),
            ToolConfig(
                name="search_files",
                category=ToolCategory.FILE_SYSTEM,
                enabled=True,
                settings={"max_results": 100}
            ),
            ToolConfig(
                name="spawn_subagent",
                category=ToolCategory.SUBAGENT,
                enabled=True,
                settings={}
            ),
        ]

    def get_enabled_tools(self) -> List[ToolConfig]:
        """Get list of enabled tools."""
        return [tool for tool in self.tools if tool.enabled]

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolConfig]:
        """Get tools by category."""
        return [tool for tool in self.tools if tool.category == category and tool.enabled]

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.enabled
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model": self.model.to_dict(),
            "tools": [
                {
                    "name": t.name,
                    "category": t.category.value,
                    "enabled": t.enabled,
                    "settings": t.settings
                }
                for t in self.tools
            ],
            "memory": {
                "enabled": self.memory.enabled,
                "max_history": self.memory.max_history,
                "persistence_enabled": self.memory.persistence_enabled,
                "persistence_path": self.memory.persistence_path,
            },
            "subagent": {
                "max_concurrent": self.subagent.max_concurrent,
                "timeout_seconds": self.subagent.timeout_seconds,
                "allowed_agents": self.subagent.allowed_agents,
            },
            "sandbox_enabled": self.sandbox_enabled,
            "logging_level": self.logging_level,
        }


def load_config_from_yaml(yaml_path: str) -> DeepAgentConfig:
    """Load Deep Agent configuration from YAML file.

    Args:
        yaml_path: Path to YAML configuration file

    Returns:
        DeepAgentConfig instance
    """
    import yaml

    path = Path(yaml_path)
    if not path.exists():
        logger.warning(f"Config file not found: {yaml_path}, using defaults")
        return DeepAgentConfig()

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    # Parse model config
    model_data = data.get("model", {})
    model = ModelConfig(
        provider=ModelProvider(model_data.get("provider", "anthropic")),
        model_id=model_data.get("model_id", "claude-3-5-sonnet-20241022"),
        temperature=model_data.get("temperature", 0.7),
        max_tokens=model_data.get("max_tokens", 4096),
        api_key_env=model_data.get("api_key_env", "ANTHROPIC_API_KEY"),
    )

    # Parse tools
    tools = []
    for tool_data in data.get("tools", []):
        tools.append(ToolConfig(
            name=tool_data["name"],
            category=ToolCategory(tool_data.get("category", "custom")),
            enabled=tool_data.get("enabled", True),
            settings=tool_data.get("settings", {}),
        ))

    # Parse memory config
    memory_data = data.get("memory", {})
    memory = MemoryConfig(
        enabled=memory_data.get("enabled", True),
        max_history=memory_data.get("max_history", 50),
        persistence_enabled=memory_data.get("persistence_enabled", False),
        persistence_path=memory_data.get("persistence_path", "data/memory"),
    )

    # Parse subagent config
    subagent_data = data.get("subagent", {})
    subagent = SubAgentConfig(
        max_concurrent=subagent_data.get("max_concurrent", 5),
        timeout_seconds=subagent_data.get("timeout_seconds", 300),
        allowed_agents=subagent_data.get("allowed_agents", []),
    )

    return DeepAgentConfig(
        model=model,
        tools=tools if tools else None,
        memory=memory,
        subagent=subagent,
        sandbox_enabled=data.get("sandbox_enabled", True),
        logging_level=data.get("logging_level", "INFO"),
    )


# Global default configuration instance
_default_config: Optional[DeepAgentConfig] = None


def get_default_config() -> DeepAgentConfig:
    """Get the default Deep Agent configuration.

    Returns:
        Default DeepAgentConfig instance
    """
    global _default_config
    if _default_config is None:
        _default_config = DeepAgentConfig()
    return _default_config


def set_default_config(config: DeepAgentConfig) -> None:
    """Set the default Deep Agent configuration.

    Args:
        config: Configuration to set as default
    """
    global _default_config
    _default_config = config
    logger.info("Updated default Deep Agent configuration")
