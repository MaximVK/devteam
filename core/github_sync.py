import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class GitHubSettings(BaseModel):
    token: str
    repo_name: str
    organization: Optional[str] = None


class GitHubTask(BaseModel):
    issue_number: int
    title: str
    body: str
    labels: List[str] = []
    assignee: Optional[str] = None
    state: str = "open"
    created_at: datetime
    updated_at: datetime


class PRMetadata(BaseModel):
    number: int
    title: str
    branch: str
    base_branch: str = "main"
    author: str
    reviewer: Optional[str] = None
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.now)


class GitHubSync:
    def __init__(self, settings: GitHubSettings):
        self.settings = settings
        self.github = Github(auth=None, login_or_token=settings.token)
        self.repo = self._get_repo()
        
    def _get_repo(self):
        try:
            if self.settings.organization:
                return self.github.get_organization(self.settings.organization).get_repo(self.settings.repo_name)
            else:
                return self.github.get_user().get_repo(self.settings.repo_name)
        except GithubException as e:
            logger.error(f"Failed to access repository: {e}")
            raise
            
    async def get_tasks_for_role(self, role: str) -> List[GitHubTask]:
        """Fetch GitHub issues tagged for a specific role"""
        try:
            issues = self.repo.get_issues(state="open", labels=[f"role:{role}"])
            tasks = []
            
            for issue in issues:
                task = GitHubTask(
                    issue_number=issue.number,
                    title=issue.title,
                    body=issue.body or "",
                    labels=[label.name for label in issue.labels],
                    assignee=issue.assignee.login if issue.assignee else None,
                    state=issue.state,
                    created_at=issue.created_at,
                    updated_at=issue.updated_at
                )
                tasks.append(task)
                
            return tasks
            
        except GithubException as e:
            logger.error(f"Failed to fetch issues: {e}")
            return []
            
    async def create_issue(self, title: str, body: str, labels: List[str], 
                          assignee: Optional[str] = None) -> Optional[int]:
        """Create a new GitHub issue"""
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels,
                assignee=assignee
            )
            logger.info(f"Created issue #{issue.number}: {title}")
            return issue.number
            
        except GithubException as e:
            logger.error(f"Failed to create issue: {e}")
            return None
            
    async def update_issue_status(self, issue_number: int, state: str, 
                                 comment: Optional[str] = None) -> bool:
        """Update issue status and optionally add a comment"""
        try:
            issue = self.repo.get_issue(issue_number)
            
            if comment:
                issue.create_comment(comment)
                
            if state in ["closed", "open"]:
                issue.edit(state=state)
                
            logger.info(f"Updated issue #{issue_number} to {state}")
            return True
            
        except GithubException as e:
            logger.error(f"Failed to update issue: {e}")
            return False
            
    async def create_pull_request(self, title: str, body: str, head_branch: str,
                                 base_branch: str = "main", reviewer: Optional[str] = None) -> Optional[PRMetadata]:
        """Create a new pull request"""
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            if reviewer:
                pr.create_review_request(reviewers=[reviewer])
                
            metadata = PRMetadata(
                number=pr.number,
                title=title,
                branch=head_branch,
                base_branch=base_branch,
                author=pr.user.login,
                reviewer=reviewer,
                status="open"
            )
            
            logger.info(f"Created PR #{pr.number}: {title}")
            return metadata
            
        except GithubException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
            
    async def get_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get comments on a pull request"""
        try:
            pr = self.repo.get_pull(pr_number)
            comments = []
            
            # Get issue comments
            for comment in pr.get_issue_comments():
                comments.append({
                    "id": comment.id,
                    "author": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at,
                    "type": "issue_comment"
                })
                
            # Get review comments
            for comment in pr.get_review_comments():
                comments.append({
                    "id": comment.id,
                    "author": comment.user.login,
                    "body": comment.body,
                    "path": comment.path,
                    "line": comment.line,
                    "created_at": comment.created_at,
                    "type": "review_comment"
                })
                
            return sorted(comments, key=lambda x: x["created_at"])
            
        except GithubException as e:
            logger.error(f"Failed to get PR comments: {e}")
            return []
            
    async def add_pr_comment(self, pr_number: int, comment: str) -> bool:
        """Add a comment to a pull request"""
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            logger.info(f"Added comment to PR #{pr_number}")
            return True
            
        except GithubException as e:
            logger.error(f"Failed to add PR comment: {e}")
            return False
            
    async def merge_pr(self, pr_number: int, commit_message: Optional[str] = None) -> bool:
        """Merge a pull request"""
        try:
            pr = self.repo.get_pull(pr_number)
            
            if pr.mergeable:
                pr.merge(commit_message=commit_message)
                logger.info(f"Merged PR #{pr_number}")
                return True
            else:
                logger.warning(f"PR #{pr_number} is not mergeable")
                return False
                
        except GithubException as e:
            logger.error(f"Failed to merge PR: {e}")
            return False
            
    async def assign_issue_to_role(self, issue_number: int, role: str) -> bool:
        """Add role label to an issue"""
        try:
            issue = self.repo.get_issue(issue_number)
            issue.add_to_labels(f"role:{role}")
            logger.info(f"Assigned issue #{issue_number} to role {role}")
            return True
            
        except GithubException as e:
            logger.error(f"Failed to assign issue: {e}")
            return False