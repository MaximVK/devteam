"""Unit tests for GitHubSync"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from core.github_sync import GitHubSync, GitHubSettings, GitHubTask, PRMetadata


class TestGitHubSync:
    """Test GitHubSync functionality"""
    
    def test_initialization(self, github_sync, github_settings):
        """Test GitHub sync initialization"""
        assert github_sync.settings == github_settings
        assert github_sync.repo is not None
        
    def test_get_repo_with_organization(self, github_settings, mock_github):
        """Test repository access with organization"""
        with patch('core.github_sync.Github', return_value=mock_github[0]):
            sync = GitHubSync(github_settings)
            # The _get_repo is called in __init__, so check it was called correctly
            mock_github[0].get_organization.assert_called_once_with("test-org")
            mock_github[0].get_organization().get_repo.assert_called_once_with("test-repo")
            
    def test_get_repo_without_organization(self, mock_github):
        """Test repository access without organization"""
        settings = GitHubSettings(
            token="test-token",
            repo_name="test-repo"
        )
        
        with patch('core.github_sync.Github', return_value=mock_github[0]):
            sync = GitHubSync(settings)
            # The _get_repo is called in __init__, so check it was called correctly
            mock_github[0].get_user.assert_called_once()
            mock_github[0].get_user().get_repo.assert_called_once_with("test-repo")
            
    @pytest.mark.asyncio
    async def test_get_tasks_for_role(self, github_sync, mock_github):
        """Test fetching tasks for a specific role"""
        tasks = await github_sync.get_tasks_for_role("backend")
        
        assert len(tasks) == 1
        assert isinstance(tasks[0], GitHubTask)
        assert tasks[0].issue_number == 1
        assert tasks[0].title == "Test issue"
        assert tasks[0].body == "Test description"
        assert "role:backend" in tasks[0].labels
        
        # Verify correct API call
        mock_github[1].get_issues.assert_called_once_with(
            state="open",
            labels=["role:backend"]
        )
        
    @pytest.mark.asyncio
    async def test_get_tasks_for_role_error(self, github_sync, mock_github):
        """Test error handling when fetching tasks"""
        from github import GithubException
        mock_github[1].get_issues.side_effect = GithubException(404, "Not found")
        
        tasks = await github_sync.get_tasks_for_role("backend")
        
        assert tasks == []
        
    @pytest.mark.asyncio
    async def test_create_issue(self, github_sync, mock_github):
        """Test creating a new issue"""
        issue_number = await github_sync.create_issue(
            title="New feature",
            body="Implement new API endpoint",
            labels=["enhancement", "role:backend"],
            assignee="test-user"
        )
        
        assert issue_number == 1
        
        mock_github[1].create_issue.assert_called_once_with(
            title="New feature",
            body="Implement new API endpoint",
            labels=["enhancement", "role:backend"],
            assignee="test-user"
        )
        
    @pytest.mark.asyncio
    async def test_create_issue_error(self, github_sync, mock_github):
        """Test error handling when creating issue"""
        from github import GithubException
        mock_github[1].create_issue.side_effect = GithubException(500, "Server error")
        
        issue_number = await github_sync.create_issue(
            title="Test",
            body="Test",
            labels=[]
        )
        
        assert issue_number is None
        
    @pytest.mark.asyncio
    async def test_update_issue_status(self, github_sync, mock_github):
        """Test updating issue status"""
        issue = Mock()
        mock_github[1].get_issue.return_value = issue
        
        success = await github_sync.update_issue_status(
            issue_number=1,
            state="closed",
            comment="Fixed in PR #123"
        )
        
        assert success is True
        issue.create_comment.assert_called_once_with("Fixed in PR #123")
        issue.edit.assert_called_once_with(state="closed")
        
    @pytest.mark.asyncio
    async def test_update_issue_status_no_comment(self, github_sync, mock_github):
        """Test updating issue without comment"""
        issue = Mock()
        mock_github[1].get_issue.return_value = issue
        
        success = await github_sync.update_issue_status(1, "open")
        
        assert success is True
        issue.create_comment.assert_not_called()
        issue.edit.assert_called_once_with(state="open")
        
    @pytest.mark.asyncio
    async def test_create_pull_request(self, github_sync, mock_github):
        """Test creating a pull request"""
        pr_metadata = await github_sync.create_pull_request(
            title="Fix: Update user endpoint",
            body="This PR fixes the user update endpoint",
            head_branch="fix/user-update",
            base_branch="main",
            reviewer="qa-bot"
        )
        
        assert pr_metadata is not None
        assert pr_metadata.number == 1
        assert pr_metadata.title == "Fix: Update user endpoint"
        assert pr_metadata.branch == "fix/user-update"
        assert pr_metadata.reviewer == "qa-bot"
        
        # Verify API calls
        mock_github[1].create_pull.assert_called_once()
        pr = mock_github[1].create_pull.return_value
        pr.create_review_request.assert_called_once_with(reviewers=["qa-bot"])
        
    @pytest.mark.asyncio
    async def test_create_pull_request_no_reviewer(self, github_sync, mock_github):
        """Test creating PR without reviewer"""
        pr_metadata = await github_sync.create_pull_request(
            title="Test PR",
            body="Test",
            head_branch="feature/test"
        )
        
        assert pr_metadata is not None
        pr = mock_github[1].create_pull.return_value
        pr.create_review_request.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_get_pr_comments(self, github_sync, mock_github):
        """Test getting PR comments"""
        pr = Mock()
        
        # Mock issue comments
        issue_comment = Mock()
        issue_comment.id = 1
        issue_comment.user.login = "user1"
        issue_comment.body = "Looks good!"
        issue_comment.created_at = datetime(2024, 1, 1, 10, 0)
        
        # Mock review comments
        review_comment = Mock()
        review_comment.id = 2
        review_comment.user.login = "user2"
        review_comment.body = "Fix this line"
        review_comment.path = "src/main.py"
        review_comment.line = 42
        review_comment.created_at = datetime(2024, 1, 1, 11, 0)
        
        pr.get_issue_comments.return_value = [issue_comment]
        pr.get_review_comments.return_value = [review_comment]
        
        mock_github[1].get_pull.return_value = pr
        
        comments = await github_sync.get_pr_comments(1)
        
        assert len(comments) == 2
        assert comments[0]["type"] == "issue_comment"
        assert comments[0]["body"] == "Looks good!"
        assert comments[1]["type"] == "review_comment"
        assert comments[1]["path"] == "src/main.py"
        assert comments[1]["line"] == 42
        
    @pytest.mark.asyncio
    async def test_add_pr_comment(self, github_sync, mock_github):
        """Test adding comment to PR"""
        pr = Mock()
        mock_github[1].get_pull.return_value = pr
        
        success = await github_sync.add_pr_comment(1, "LGTM! 🚀")
        
        assert success is True
        pr.create_issue_comment.assert_called_once_with("LGTM! 🚀")
        
    @pytest.mark.asyncio
    async def test_merge_pr_success(self, github_sync, mock_github):
        """Test merging a PR successfully"""
        pr = Mock()
        pr.mergeable = True
        mock_github[1].get_pull.return_value = pr
        
        success = await github_sync.merge_pr(1, "Merge PR #1")
        
        assert success is True
        pr.merge.assert_called_once_with(commit_message="Merge PR #1")
        
    @pytest.mark.asyncio
    async def test_merge_pr_not_mergeable(self, github_sync, mock_github):
        """Test merging PR that's not mergeable"""
        pr = Mock()
        pr.mergeable = False
        mock_github[1].get_pull.return_value = pr
        
        success = await github_sync.merge_pr(1)
        
        assert success is False
        pr.merge.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_assign_issue_to_role(self, github_sync, mock_github):
        """Test assigning issue to a role"""
        issue = Mock()
        mock_github[1].get_issue.return_value = issue
        
        success = await github_sync.assign_issue_to_role(1, "frontend")
        
        assert success is True
        issue.add_to_labels.assert_called_once_with("role:frontend")
        
    @pytest.mark.asyncio
    async def test_error_handling(self, github_sync, mock_github):
        """Test comprehensive error handling"""
        from github import GithubException
        # Test various API errors
        mock_github[1].get_issue.side_effect = GithubException(404, "Not found")
        
        success = await github_sync.update_issue_status(1, "closed")
        assert success is False
        
        mock_github[1].create_pull.side_effect = GithubException(500, "Server error")
        pr = await github_sync.create_pull_request("Test", "Test", "test")
        assert pr is None
        
        mock_github[1].get_pull.side_effect = GithubException(404, "Not found")
        comments = await github_sync.get_pr_comments(1)
        assert comments == []