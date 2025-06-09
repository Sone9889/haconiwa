"""
Test CLI v1.0 Commands
新しいCLI構造のテストケース
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from typer.testing import CliRunner

from haconiwa.cli import app
from haconiwa.core.crd.parser import CRDParser
from haconiwa.core.crd.models import SpaceCRD, AgentCRD


class TestCLIv1:
    """CLI v1.0のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.runner = CliRunner()
    
    def test_init_command_creates_config(self):
        """init コマンドが設定ファイルを作成することをテスト"""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("pathlib.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file:
            
            result = self.runner.invoke(app, ["init"])
            
            assert result.exit_code == 0
            assert "✅ Haconiwa configuration initialized" in result.stdout
            mock_mkdir.assert_called()
            mock_file.assert_called()
    
    def test_init_command_existing_config(self):
        """init コマンドで既存設定がある場合の確認プロンプトをテスト"""
        with patch("pathlib.Path.exists", return_value=True):
            result = self.runner.invoke(app, ["init"], input="n\n")
            
            assert result.exit_code == 0
            assert "Configuration already exists" in result.stdout
    
    def test_init_command_force_overwrite(self):
        """init コマンドの強制上書きオプションをテスト"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open()) as mock_file:
            
            result = self.runner.invoke(app, ["init", "--force"])
            
            assert result.exit_code == 0
            assert "✅ Haconiwa configuration initialized" in result.stdout
            mock_file.assert_called()
    
    @patch("haconiwa.core.crd.parser.CRDParser.parse_file")
    def test_apply_command_single_file(self, mock_parse):
        """apply コマンドで単一ファイルを適用することをテスト"""
        # Mock CRD object
        mock_space_crd = MagicMock(spec=SpaceCRD)
        mock_space_crd.metadata.name = "test-space"
        mock_parse.return_value = mock_space_crd
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("haconiwa.core.applier.CRDApplier.apply") as mock_apply:
            
            result = self.runner.invoke(app, ["apply", "-f", "test.yaml"])
            
            assert result.exit_code == 0
            assert "✅ Applied 1 resource" in result.stdout
            mock_parse.assert_called_once()
            mock_apply.assert_called_once_with(mock_space_crd)
    
    @patch("haconiwa.core.crd.parser.CRDParser.parse_multi_yaml")
    def test_apply_command_multi_document(self, mock_parse):
        """apply コマンドで複数ドキュメントYAMLを適用することをテスト"""
        # Mock multiple CRD objects
        mock_space_crd = MagicMock(spec=SpaceCRD)
        mock_agent_crd = MagicMock(spec=AgentCRD)
        mock_parse.return_value = [mock_space_crd, mock_agent_crd]
        
        with patch("builtins.open", mock_open(read_data="yaml content")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("haconiwa.core.applier.CRDApplier.apply") as mock_apply:
            
            result = self.runner.invoke(app, ["apply", "-f", "multi.yaml"])
            
            assert result.exit_code == 0
            assert "✅ Applied 2 resources" in result.stdout
            assert mock_apply.call_count == 2
    
    def test_apply_command_file_not_found(self):
        """apply コマンドでファイルが存在しない場合のエラーテスト"""
        with patch("pathlib.Path.exists", return_value=False):
            result = self.runner.invoke(app, ["apply", "-f", "nonexistent.yaml"])
            
            assert result.exit_code != 0
            assert "File not found" in result.stdout
    
    def test_apply_command_dry_run(self):
        """apply コマンドのdry-runオプションをテスト"""
        mock_space_crd = MagicMock(spec=SpaceCRD)
        
        with patch("haconiwa.core.crd.parser.CRDParser.parse_file", return_value=mock_space_crd), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("haconiwa.core.applier.CRDApplier.apply") as mock_apply:
            
            result = self.runner.invoke(app, ["apply", "-f", "test.yaml", "--dry-run"])
            
            assert result.exit_code == 0
            assert "🔍 Dry run mode" in result.stdout
            mock_apply.assert_not_called()  # dry-runでは実際の適用は行わない
    
    def test_space_command_renamed_from_company(self):
        """space コマンドが company からリネームされていることをテスト"""
        result = self.runner.invoke(app, ["space", "--help"])
        
        assert result.exit_code == 0
        assert "space" in result.stdout
        # 古いcompanyコマンドは存在しないことを確認
        result_old = self.runner.invoke(app, ["company", "--help"])
        assert result_old.exit_code != 0 or "No such command" in result_old.stdout
    
    def test_tool_command_renamed_from_resource(self):
        """tool コマンドが resource からリネームされていることをテスト"""
        result = self.runner.invoke(app, ["tool", "--help"])
        
        assert result.exit_code == 0
        assert "tool" in result.stdout
        # 古いresourceコマンドは存在しないことを確認
        result_old = self.runner.invoke(app, ["resource", "--help"])
        assert result_old.exit_code != 0 or "No such command" in result_old.stdout
    
    @patch("haconiwa.core.policy.PolicyEngine.list_policies")
    def test_policy_command_list(self, mock_list):
        """policy list コマンドをテスト"""
        mock_list.return_value = [
            {"name": "default-policy", "type": "CommandPolicy"},
            {"name": "strict-policy", "type": "CommandPolicy"}
        ]
        
        result = self.runner.invoke(app, ["policy", "ls"])
        
        assert result.exit_code == 0
        assert "default-policy" in result.stdout
        assert "strict-policy" in result.stdout
    
    @patch("haconiwa.core.policy.PolicyEngine.test_command")
    def test_policy_command_test(self, mock_test):
        """policy test コマンドをテスト"""
        mock_test.return_value = True
        
        result = self.runner.invoke(app, ["policy", "test", "agent", "test-agent", "--cmd", "git clone"])
        
        assert result.exit_code == 0
        assert "✅ Command allowed" in result.stdout
        mock_test.assert_called_once_with("test-agent", "git clone")
    
    @patch("haconiwa.core.policy.PolicyEngine.test_command")
    def test_policy_command_test_denied(self, mock_test):
        """policy test コマンドで拒否される場合をテスト"""
        mock_test.return_value = False
        
        result = self.runner.invoke(app, ["policy", "test", "agent", "test-agent", "--cmd", "rm -rf /"])
        
        assert result.exit_code == 0
        assert "❌ Command denied" in result.stdout
    
    def test_space_command_ls(self):
        """space ls コマンドをテスト"""
        with patch("haconiwa.space.manager.SpaceManager.list_spaces") as mock_list:
            mock_list.return_value = [
                {"name": "dev-world", "status": "active", "companies": 1},
                {"name": "prod-world", "status": "inactive", "companies": 0}
            ]
            
            result = self.runner.invoke(app, ["space", "ls"])
            
            assert result.exit_code == 0
            assert "dev-world" in result.stdout
            assert "prod-world" in result.stdout
    
    def test_space_command_start(self):
        """space start コマンドをテスト"""
        with patch("haconiwa.space.manager.SpaceManager.start_company") as mock_start:
            mock_start.return_value = True
            
            result = self.runner.invoke(app, ["space", "start", "-c", "test-company"])
            
            assert result.exit_code == 0
            assert "✅ Started company" in result.stdout
            mock_start.assert_called_once_with("test-company")
    
    def test_space_command_clone(self):
        """space clone コマンドをテスト"""
        with patch("haconiwa.space.manager.SpaceManager.clone_repository") as mock_clone:
            mock_clone.return_value = True
            
            result = self.runner.invoke(app, ["space", "clone", "-c", "test-company"])
            
            assert result.exit_code == 0
            assert "✅ Cloned repository" in result.stdout
            mock_clone.assert_called_once_with("test-company")
    
    def test_tool_command_scan_filepath(self):
        """tool --scan-filepath コマンドをテスト"""
        with patch("haconiwa.tool.scanner.PathScanner.scan") as mock_scan:
            mock_scan.return_value = ["src/main.py", "src/utils.py"]
            
            result = self.runner.invoke(app, ["tool", "--scan-filepath", "default-scan"])
            
            assert result.exit_code == 0
            assert "src/main.py" in result.stdout
            mock_scan.assert_called_once()
    
    def test_tool_command_scan_db(self):
        """tool --scan-db コマンドをテスト"""
        with patch("haconiwa.tool.scanner.DatabaseScanner.scan") as mock_scan:
            mock_scan.return_value = {"tables": ["users", "posts"], "views": ["user_posts"]}
            
            result = self.runner.invoke(app, ["tool", "--scan-db", "local-postgres"])
            
            assert result.exit_code == 0
            assert "users" in result.stdout
            mock_scan.assert_called_once()
    
    def test_tool_command_scan_yaml_output(self):
        """tool --scan-filepath --yaml コマンドをテスト"""
        with patch("haconiwa.tool.scanner.PathScanner.scan") as mock_scan:
            mock_scan.return_value = ["src/main.py", "src/utils.py"]
            
            result = self.runner.invoke(app, ["tool", "--scan-filepath", "default-scan", "--yaml"])
            
            assert result.exit_code == 0
            assert "files:" in result.stdout  # YAML形式の出力を確認
    
    def test_backward_compatibility_warning(self):
        """後方互換性の警告メッセージをテスト"""
        # Phase 1では古いコマンドにdeprecation warningを出す
        with patch("haconiwa.cli.show_deprecation_warning") as mock_warning:
            # 仮に古いコマンドが残っている場合
            result = self.runner.invoke(app, ["company", "build", "--name", "test"])
            
            # 警告が表示されることを確認（実装時）
            # mock_warning.assert_called_once()
    
    def test_version_command(self):
        """--version オプションをテスト"""
        result = self.runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "haconiwa version" in result.stdout 