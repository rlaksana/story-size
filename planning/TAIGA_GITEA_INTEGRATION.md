# Taiga + Gitea Integration Plan for Intelligence Learning

## Overview

This document outlines how to integrate story-size with Taiga (project management) and Gitea (git hosting) to create a complete learning ecosystem for story point estimation.

## API Capabilities Analysis

### Taiga API
```yaml
endpoints:
  issues:
    list: GET /api/v1/issues?project={project_id}
    detail: GET /api/v1/issues/{id}
    update: PATCH /api/v1/issues/{id}
    create: POST /api/v1/issues

  user_stories:
    list: GET /api/v1/userstories?project={project_id}
    detail: GET /api/v1/userstories/{id}
    update: PATCH /api/v1/userstories/{id}
    create: POST /api/v1/userstories

  tasks:
    list: GET /api/v1/tasks?project={project_id}
    detail: GET /api/v1/tasks/{id}
    update: PATCH /api/v1/tasks/{id}

  milestones/sprints:
    list: GET /api/v1/milestones?project={project_id}
    detail: GET /api/v1/milestones/{id}
    stats: GET /api/v1/milestones/{id}/stats

  project:
    detail: GET /api/v1/projects/{id}
    stats: GET /api/v1/projects/{id}/stats

  history:
    detail: GET /api/v1/history/userstory/{id}
```

### Gitea API
```yaml
endpoints:
  repositories:
    detail: GET /api/v1/repos/{owner}/{repo}
    commits: GET /api/v1/repos/{owner}/{repo}/commits
    branches: GET /api/v1/repos/{owner}/{repo}/branches

  pull_requests:
    list: GET /api/v1/repos/{owner}/{repo}/pulls
    detail: GET /api/v1/repos/{owner}/{repo}/pulls/{number}
    diff: GET /api/v1/repos/{owner}/{repo}/pulls/{number}.diff
    stats: GET /api/v1/repos/{owner}/{repo}/pulls/{number}

  issues:
    list: GET /api/v1/repos/{owner}/{repo}/issues
    detail: GET /api/v1/repos/{owner}/{repo}/issues/{number}

  webhook:
    create: POST /api/v1/repos/{owner}/{repo}/hooks

  commits:
    detail: GET /api/v1/repos/{owner}/{repo}/git/commits/{sha}
    stats: GET /api/v1/repos/{owner}/{repo}/git/commits/{sha}/stats
```

## Implementation Architecture

### Data Flow Architecture
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Taiga     │◄────│ story-size   │────►│   Gitea     │
│ (User Stories│     │ (AI Engine)  │     │ (Code/PRs)  │
│ & Tasks)    │     │              │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Story Data  │     │Learning DB   │     │ Code Metrics │
│ (Estimates) │     │ (SQLite/PG)  │     │ (PR Sizes)  │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Phase 1: Taiga Integration (Week 1)

### 1.1 Taiga Client Implementation
```python
# story_size/integrations/taiga_client.py
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

class TaigaClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json',
            'x-disable-pagination': 'True'  # Get all results
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    async def get_project_by_slug(self, slug: str) -> Dict:
        """Get project details by slug"""
        response = self.session.get(f"{self.base_url}/api/v1/projects/by_slug?slug={slug}")
        response.raise_for_status()
        return response.json()

    async def get_user_stories(self, project_id: int, status__is_closed: bool = False) -> List[Dict]:
        """Get all user stories for a project"""
        params = {
            'project': project_id,
            'status__is_closed': status__is_closed
        }
        response = self.session.get(f"{self.base_url}/api/v1/userstories", params=params)
        response.raise_for_status()
        return response.json()

    async def get_story_with_tasks(self, story_id: int) -> Dict:
        """Get story details with all associated tasks"""
        # Get story
        story_response = self.session.get(f"{self.base_url}/api/v1/userstories/{story_id}")
        story = story_response.json()

        # Get associated tasks
        tasks_response = self.session.get(f"{self.base_url}/api/v1/tasks?user_story={story_id}")
        story['tasks'] = tasks_response.json()

        # Get history
        history_response = self.session.get(f"{self.base_url}/api/v1/history/userstory/{story_id}")
        story['history'] = history_response.json()

        return story

    async def update_story_points(self, story_id: int, points: int, comment: str = None):
        """Update story points with optional comment"""
        data = {
            'version': await self.get_story_version(story_id),
            'points': points
        }

        response = self.session.patch(f"{self.base_url}/api/v1/userstories/{story_id}", json=data)
        response.raise_for_status()

        if comment:
            await self.add_story_comment(story_id, comment)

        return response.json()

    async def add_story_comment(self, story_id: int, comment: str):
        """Add a comment to a user story"""
        data = {
            'comment': comment
        }
        response = self.session.post(f"{self.base_url}/api/v1/history/userstory/{story_id}", json=data)
        response.raise_for_status()
        return response.json()

    async def get_sprint_stats(self, project_id: int, sprint_id: int) -> Dict:
        """Get sprint statistics including velocity"""
        response = self.session.get(f"{self.base_url}/api/v1/milestones/{sprint_id}/stats")
        response.raise_for_status()
        return response.json()

    async def get_closed_stories_with_actuals(self, project_id: int, days_back: int = 90) -> List[Dict]:
        """Get recently completed stories for learning data"""
        # Calculate date filter
        from_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        # Get closed stories
        params = {
            'project': project_id,
            'status__is_closed': True,
            'modified_date__gte': from_date
        }

        response = self.session.get(f"{self.base_url}/api/v1/userstories", params=params)
        stories = response.json()

        # Enrich with task completion data
        for story in stories:
            story['tasks'] = await self.get_story_tasks(story['id'])
            story['completion_metrics'] = self.calculate_completion_metrics(story)

        return stories

    def calculate_completion_metrics(self, story: Dict) -> Dict:
        """Calculate actual completion metrics from story data"""
        tasks = story.get('tasks', [])

        # Calculate total planned vs actual
        planned_tasks = len([t for t in tasks if t.get('is_closed')])
        total_tasks = len(tasks)

        # Calculate completion dates
        created_date = datetime.fromisoformat(story['created_date'])
        modified_date = datetime.fromisoformat(story['modified_date'])
        duration_days = (modified_date - created_date).days

        return {
            'planned_tasks': planned_tasks,
            'total_tasks': total_tasks,
            'completion_percentage': (planned_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'duration_days': duration_days,
            'task_completion_rate': planned_tasks / total_tasks if total_tasks > 0 else 0
        }
```

### 1.2 Taiga Webhook Handler
```python
# story_size/integrations/taiga_webhooks.py
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import hmac
import hashlib

app = FastAPI()

class TaigaWebhookHandler:
    def __init__(self, story_size_engine):
        self.engine = story_size_engine
        self.webhook_secret = os.getenv('TAIGA_WEBHOOK_SECRET')

    def verify_webhook(self, request_body: bytes, signature: str) -> bool:
        """Verify webhook signature from Taiga"""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            request_body,
            hashlib.sha1
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

@app.post("/webhooks/taiga")
async def handle_taiga_webhook(request: Request, x_taiga_webhook_signature: str):
    """Handle Taiga webhook events"""

    # Verify webhook
    body = await request.body()
    if not webhook_handler.verify_webhook(body, x_taiga_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse event
    event = await request.json()

    # Route to appropriate handler
    if event['type'] == 'userstory.change':
        await handle_story_change(event)
    elif event['type'] == 'milestone.change':
        await handle_sprint_change(event)
    elif event['type'] == 'task.change':
        await handle_task_change(event)

    return {"status": "processed"}

async def handle_story_change(event: Dict[str, Any]):
    """Handle user story change events"""
    data = event['data']

    # Check if story was just completed
    if data.get('status') == 'closed' and data.get('status_diff', {}).get('status') == 'open':
        # Story was just closed - collect learning data
        await collect_story_completion_data(data['id'])

    # Check if points were updated
    if 'points_diff' in data:
        # Analyze estimation correction
        await analyze_estimation_correction(data)

async def collect_story_completion_data(story_id: int):
    """Collect actual completion data for learning"""
    # Get full story data
    story = await taiga_client.get_story_with_tasks(story_id)

    # Calculate actual metrics
    actual_metrics = {
        'story_id': story_id,
        'estimated_points': story.get('points', 0),
        'actual_points': await calculate_actual_points(story),
        'task_count': len(story.get('tasks', [])),
        'completed_tasks': len([t for t in story.get('tasks', []) if t.get('is_closed')]),
        'duration_days': calculate_duration(story),
        'created_date': story['created_date'],
        'completed_date': story['modified_date']
    }

    # Get linked code changes
    code_metrics = await get_code_changes_for_story(story_id)
    actual_metrics.update(code_metrics)

    # Store for learning
    await learning_db.store_completion_data(actual_metrics)

    # Trigger model update
    await trigger_learning_update()
```

## Phase 2: Gitea Integration (Week 2)

### 2.1 Gitea Client Implementation
```python
# story_size/integrations/gitea_client.py
import requests
from typing import Dict, List, Optional
import re

class GiteaClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/json'
        }

    async def get_pr_by_story_id(self, story_id: int) -> List[Dict]:
        """Find pull requests related to a Taiga story"""
        # Search PRs by story ID in title or description
        search_terms = [f"#{story_id}", f"story-{story_id}", f"issue-{story_id}"]

        all_prs = []
        for repo in await self.get_all_repos():
            prs = await self.search_prs_by_terms(repo['full_name'], search_terms)
            all_prs.extend(prs)

        return all_prs

    async def get_pr_metrics(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Get detailed metrics for a pull request"""
        pr = await self.get_pr_details(owner, repo, pr_number)

        # Get commit stats
        commits_response = self.session.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        )
        commits = commits_response.json()

        # Calculate metrics
        total_additions = sum(c['stats'].get('additions', 0) for c in commits if c.get('stats'))
        total_deletions = sum(c['stats'].get('deletions', 0) for c in commits if c.get('stats'))
        files_changed = len(set(f['filename'] for c in commits for f in c.get('files', [])))

        # Analyze complexity
        complexity_indicators = await self.analyze_code_complexity(commits)

        return {
            'pr_number': pr_number,
            'title': pr['title'],
            'description': pr['body'],
            'commits_count': len(commits),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'files_changed': files_changed,
            'complexity_score': complexity_indicators['score'],
            'estimated_hours': complexity_indicators.get('estimated_hours'),
            'test_files_count': complexity_indicators.get('test_files', 0),
            'config_files_count': complexity_indicators.get('config_files', 0),
            'languages_used': complexity_indicators.get('languages', []),
            'merge_conflicts': pr.get('mergeable') == False,
            'requested_reviewers': len(pr.get('requested_reviewers', [])),
            'approvals': pr.get('review', {}).get('approved_reviewers', [])
        }

    async def analyze_code_complexity(self, commits: List[Dict]) -> Dict:
        """Analyze code complexity from commits"""
        complexity_score = 0
        languages = set()
        test_files = 0
        config_files = 0

        for commit in commits:
            if not commit.get('files'):
                continue

            for file in commit['files']:
                filename = file['filename']
                changes = file.get('changes', {})

                # Count file types
                if any(test in filename for test in ['test', 'spec']):
                    test_files += 1
                elif any(ext in filename for ext in ['.yml', '.yaml', '.json', '.toml', '.ini']):
                    config_files += 1

                # Detect languages
                if '.' in filename:
                    ext = filename.split('.')[-1]
                    languages.add(ext)

                # Calculate complexity score
                additions = changes.get('additions', 0)
                deletions = changes.get('deletions', 0)
                total_changes = additions + deletions

                # Weighted complexity based on file type and changes
                if filename.endswith(('.py', '.js', '.ts', '.cs', '.java')):
                    complexity_score += total_changes * 1.2
                elif filename.endswith(('.html', '.css', '.scss', '.vue', '.jsx')):
                    complexity_score += total_changes * 0.8
                else:
                    complexity_score += total_changes * 0.5

        # Estimate hours (rough approximation: 1 complexity point = 0.5 hours)
        estimated_hours = complexity_score * 0.5

        return {
            'score': complexity_score,
            'estimated_hours': estimated_hours,
            'test_files': test_files,
            'config_files': config_files,
            'languages': list(languages)
        }
```

### 2.2 Gitea Webhook Setup
```python
# story_size/integrations/gitea_webhooks.py
@app.post("/webhooks/gitea")
async def handle_gitea_webhook(request: Request):
    """Handle Gitea webhook events"""

    # Parse event
    event = await request.json()

    # Route handlers
    if 'pull_request' in event:
        await handle_pr_event(event)
    elif 'push' in event:
        await handle_push_event(event)
    elif 'issues' in event:
        await handle_issue_event(event)

    return {"status": "processed"}

async def handle_pr_event(event: Dict):
    """Handle pull request events"""
    pr = event['pull_request']
    action = event['action']

    if action in ['opened', 'synchronized']:
        # PR was opened or updated
        await analyze_pr_for_estimation(pr)
    elif action == 'closed' and pr.get('merged'):
        # PR was merged - link to story completion
        await link_pr_to_story_completion(pr)

async def analyze_pr_for_estimation(pr: Dict):
    """Analyze PR to update related story estimates"""
    # Extract story ID from PR
    story_id = extract_story_id_from_pr(pr)

    if story_id:
        # Get PR metrics
        metrics = await gitea_client.get_pr_metrics(
            pr['base']['repo']['owner']['login'],
            pr['base']['repo']['name'],
            pr['number']
        )

        # Update story estimate based on PR metrics
        await update_story_estimate_from_pr(story_id, metrics)

def extract_story_id_from_pr(pr: Dict) -> Optional[int]:
    """Extract Taiga story ID from PR title or description"""
    text = f"{pr['title']} {pr['body'] or ''}"

    # Look for patterns like #1234, story-1234, issue-1234
    patterns = [
        r'#(\d+)',
        r'story[-_](\d+)',
        r'issue[-_](\d+)',
        r'taiga[-_](\d+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None
```

## Phase 3: Learning Data Integration (Week 3)

### 3.1 Data Collection Pipeline
```python
# story_size/core/intelligence/data_collector.py
class TaigaGiteaDataCollector:
    def __init__(self, taiga_client: TaigaClient, gitea_client: GiteaClient):
        self.taiga = taiga_client
        self.gitea = gitea_client
        self.learning_db = LearningDatabase()

    async def collect_historical_data(self, project_slug: str, days_back: int = 180):
        """Collect comprehensive historical data for learning"""

        # Get project info
        project = await self.taiga.get_project_by_slug(project_slug)

        # Get completed stories
        completed_stories = await self.taiga.get_closed_stories_with_actuals(
            project['id'],
            days_back
        )

        learning_data = []

        for story in completed_stories:
            # Get story metadata
            story_data = {
                'story_id': story['id'],
                'title': story['subject'],
                'description': story['description'],
                'estimated_points': story['points'],
                'project_id': project['id'],
                'created_date': story['created_date'],
                'closed_date': story['modified_date'],
                'sprint_id': story.get('milestone'),
                'assigned_to': story.get('assigned_to'),
                'tags': story.get('tags', [])
            }

            # Calculate actual metrics from tasks
            story_data['actual_metrics'] = self.calculate_task_based_metrics(story)

            # Get linked code changes
            pr_metrics = await self.gitea.get_pr_by_story_id(story['id'])
            story_data['code_metrics'] = self.aggregate_pr_metrics(pr_metrics)

            # Calculate actual points based on metrics
            story_data['actual_points'] = self.calculate_actual_points(story_data)

            learning_data.append(story_data)

        # Store for learning
        await self.learning_db.bulk_insert_historical_data(learning_data)

        return learning_data

    def calculate_task_based_metrics(self, story: Dict) -> Dict:
        """Calculate actual effort metrics from story tasks"""
        tasks = story.get('tasks', [])

        # If tasks have time tracking data, use it
        total_task_hours = sum(t.get('time_spent', 0) for t in tasks)

        # Otherwise estimate from task complexity and count
        if total_task_hours == 0:
            # Estimate based on task descriptions and status changes
            task_complexity = sum(self.estimate_task_complexity(t) for t in tasks)
            total_task_hours = task_complexity * 2  # Rough conversion

        return {
            'task_count': len(tasks),
            'completed_tasks': len([t for t in tasks if t.get('is_closed')]),
            'total_task_hours': total_task_hours,
            'average_task_hours': total_task_hours / len(tasks) if tasks else 0,
            'task_completion_rate': len([t for t in tasks if t.get('is_closed')]) / len(tasks) if tasks else 0
        }

    def aggregate_pr_metrics(self, prs: List[Dict]) -> Dict:
        """Aggregate metrics from multiple PRs"""
        if not prs:
            return {}

        total_metrics = {
            'pr_count': len(prs),
            'total_commits': sum(pr['commits_count'] for pr in prs),
            'total_additions': sum(pr['total_additions'] for pr in prs),
            'total_deletions': sum(pr['total_deletions'] for pr in prs),
            'total_files_changed': sum(pr['files_changed'] for pr in prs),
            'total_complexity_score': sum(pr['complexity_score'] for pr in prs),
            'total_test_files': sum(pr['test_files_count'] for pr in prs),
            'languages': set()
        }

        # Combine languages from all PRs
        for pr in prs:
            total_metrics['languages'].update(pr['languages_used'])

        total_metrics['languages'] = list(total_metrics['languages'])

        return total_metrics

    def calculate_actual_points(self, story_data: Dict) -> int:
        """Calculate actual story points based on collected metrics"""
        task_metrics = story_data.get('actual_metrics', {})
        code_metrics = story_data.get('code_metrics', {})

        # Base calculation from task hours (8 hours = 1 story point approximation)
        actual_points = 0

        if task_metrics.get('total_task_hours', 0) > 0:
            actual_points = task_metrics['total_task_hours'] / 8

        # Adjust based on code complexity
        if code_metrics.get('total_complexity_score', 0) > 0:
            # Convert code complexity to points
            code_points = code_metrics['total_complexity_score'] / 100
            actual_points = max(actual_points, code_points)

        # Ensure minimum of 1 point
        actual_points = max(1, round(actual_points))

        return actual_points
```

## Phase 4: Continuous Learning Loop (Week 4)

### 4.1 Real-Time Learning System
```python
# story_size/core/intelligence/continuous_learner.py
class ContinuousLearningSystem:
    def __init__(self, data_collector: TaigaGiteaDataCollector):
        self.collector = data_collector
        self.model_trainer = ModelTrainer()
        self.last_training_date = None

    async def start_learning_loop(self):
        """Start the continuous learning process"""
        while True:
            try:
                # Collect new data
                new_data = await self.collect_new_completion_data()

                if new_data:
                    # Update models incrementally
                    await self.incremental_model_update(new_data)

                    # Evaluate model performance
                    performance = await self.evaluate_model_performance()

                    # Store performance metrics
                    await self.store_performance_metrics(performance)

                # Wait for next cycle (check daily)
                await asyncio.sleep(24 * 60 * 60)

            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour on error

    async def collect_new_completion_data(self):
        """Collect newly completed stories since last update"""
        # Get stories completed in last 24 hours
        cutoff_date = datetime.now() - timedelta(days=1)

        # Query Taiga for newly completed stories
        new_stories = await self.taiga.get_stories_completed_since(cutoff_date)

        learning_data = []
        for story in new_stories:
            # Enrich with code metrics
            pr_metrics = await self.gitea.get_pr_by_story_id(story['id'])
            story_data = {
                'story': story,
                'code_metrics': self.collector.aggregate_pr_metrics(pr_metrics),
                'actual_points': self.collector.calculate_actual_points({
                    'story': story,
                    'code_metrics': pr_metrics
                })
            }
            learning_data.append(story_data)

        return learning_data

    async def incremental_model_update(self, new_data: List[Dict]):
        """Update models with new data without full retraining"""
        # Extract features and labels from new data
        features = [self.extract_features(d) for d in new_data]
        labels = [d['actual_points'] for d in new_data]

        # Update pattern matcher
        await self.model_trainer.update_pattern_matcher(features, labels)

        # Update team calibration models
        await self.model_trainer.update_team_calibrations(new_data)

        # Update similarity engine embeddings
        await self.model_trainer.update_similarity_embeddings(features)

    async def generate_accuracy_report(self) -> Dict:
        """Generate monthly accuracy report"""
        # Get last month's estimates vs actuals
        monthly_data = await self.get_monthly_accuracy_data()

        # Calculate metrics
        accuracy_metrics = self.calculate_accuracy_metrics(monthly_data)

        # Generate insights
        insights = await self.generate_accuracy_insights(accuracy_metrics)

        return {
            'period': 'last_30_days',
            'total_estimates': len(monthly_data),
            'metrics': accuracy_metrics,
            'insights': insights,
            'recommendations': self.generate_recommendations(accuracy_metrics)
        }
```

## Required Setup

### Taiga Setup
1. **Enable API Access**
   - Generate API token in Taiga settings
   - Configure webhook endpoints in project settings
   - Set up user permissions

2. **Webhook Configuration**
   ```bash
   # Add these webhook URLs in Taiga project settings
   https://your-story-size-app.com/webhooks/taiga

   # Enable events:
   - User story change
   - Milestone change
   - Task change
   ```

### Gitea Setup
1. **Create Personal Access Token**
   ```bash
   # In Gitea: Settings -> Applications -> Generate New Token
   # Required scopes: read:repository, read:user, read:organization
   ```

2. **Configure Webhooks**
   ```bash
   # Add webhook in repository settings:
   # Payload URL: https://your-story-size-app.com/webhooks/gitea
   # Content type: application/json
   # Events: Pull requests, Pushes, Issues
   ```

### Environment Variables
```yaml
TAIGA_URL: "https://your-taiga-instance.com"
TAIGA_TOKEN: "your-taiga-api-token"
TAIGA_WEBHOOK_SECRET: "webhook-secret-string"

GITEA_URL: "https://your-gitea-instance.com"
GITEA_TOKEN: "your-gitea-token"

LEARNING_DB_URL: "postgresql://user:pass@localhost/story_size_learning"
```

## Benefits of Taiga + Gitea Integration

1. **Complete Data Coverage**
   - Task-level granularity from Taiga
   - Code-level metrics from Gitea
   - End-to-end story lifecycle tracking

2. **Open Source Stack**
   - No vendor lock-in
   - Full control over data
   - Customizable integration

3. **Real-Time Learning**
   - Immediate feedback from story completion
   - Continuous model improvement
   - Team-specific calibration

4. **Rich Context**
   - Task breakdown accuracy
   - Code complexity correlation
   - Sprint velocity tracking

This integration will give you a complete learning ecosystem that continuously improves estimation accuracy based on real project data. Would you like me to create implementation details for any specific part of this integration?