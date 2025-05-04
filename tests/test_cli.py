"""Tests for the CLI."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from archiver.cli import cli

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

def test_cli_version(runner):
    """Test the version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "Video Archiver ZIM" in result.output

def test_archive_command_interactive(runner, monkeypatch):
    """Test the archive command in interactive mode."""
    # Mock user inputs
    inputs = [
        "https://youtube.com/watch?v=test",
        "Test Video",
        "Test Description",
        "y"  # Confirm directory creation
    ]
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: inputs.pop(0))
    monkeypatch.setattr("rich.prompt.Confirm.ask", lambda *args, **kwargs: True)
    
    # Mock the archive_video function
    def mock_archive_video(*args, **kwargs):
        if kwargs.get("progress_callback"):
            kwargs["progress_callback"](100)
        return True
    
    monkeypatch.setattr("archiver.archiver.archive_video", mock_archive_video)
    
    result = runner.invoke(cli, ["archive"])
    assert result.exit_code == 0
    assert "Video archived successfully" in result.output

def test_archive_command_with_args(runner, monkeypatch):
    """Test the archive command with provided arguments."""
    # Mock the archive_video function
    def mock_archive_video(*args, **kwargs):
        if kwargs.get("progress_callback"):
            kwargs["progress_callback"](100)
        return True
    
    monkeypatch.setattr("archiver.archiver.archive_video", mock_archive_video)
    
    result = runner.invoke(cli, [
        "archive",
        "https://youtube.com/watch?v=test",
        "--quality", "720p",
        "--title", "Test Video",
        "--description", "Test Description",
        "--output", "./test_output"
    ])
    assert result.exit_code == 0
    assert "Video archived successfully" in result.output

def test_manage_command_interactive(runner, monkeypatch):
    """Test the manage command in interactive mode."""
    # Mock user inputs
    inputs = [
        str(Path.cwd() / "config" / "config.yaml"),
        str(Path.cwd() / "watch"),
        "y"  # Confirm directory creation
    ]
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: inputs.pop(0))
    monkeypatch.setattr("rich.prompt.Confirm.ask", lambda *args, **kwargs: True)
    
    # Mock the run_manager function
    def mock_run_manager(*args, **kwargs):
        return True
    
    monkeypatch.setattr("archiver.manager.run_manager", mock_run_manager)
    
    result = runner.invoke(cli, ["manage"])
    assert result.exit_code == 0
    assert "Starting manager in continuous mode" in result.output 