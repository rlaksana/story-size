# Practical Intelligence Plan for Story Size Estimation

## The Reality: What Actually Works

Most estimation improvements come from simple data, not complex AI. This plan focuses on the 80/20 rule - 80% of value with 20% of complexity.

## Core Hypothesis
Better estimation comes from:
1. **Historical accuracy data** - What did we estimate vs actual?
2. **Team patterns** - Some teams consistently over/under estimate
3. **Similar stories** - Past work is the best predictor
4. **Simple adjustments** - Small corrections beat complex models

## Phase 1: Data Foundation (Week 1-2)

### What to Build:
```python
# story_size/integrations/simple_collector.py
class SimpleDataCollector:
    """Collect the minimum data needed for learning"""

    def __init__(self, taiga_url, taiga_token, gitea_url, gitea_token):
        self.taiga = TaigaClient(taiga_url, taiga_token)
        self.gitea = GiteaClient(gitea_url, gitea_token)
        self.db = SQLiteConnection("story_learning.db")

    async def collect_historical_data(self, project_slug, days_back=90):
        """Get completed stories with their actual outcomes"""

        # 1. Get completed stories from Taiga
        stories = await self.taiga.get_closed_stories(project_slug, days_back)

        for story in stories:
            # 2. Extract basic metrics
            story_data = {
                'story_id': story['id'],
                'title': story['subject'],
                'description': story['description'][:500],  # First 500 chars
                'estimated_points': story.get('points', 0),
                'created_date': story['created_date'],
                'completed_date': story['modified_date'],
                'team_id': story.get('assigned_to', 'unassigned'),
                'tags': story.get('tags', [])
            }

            # 3. Find linked PRs from Gitea
            prs = await self.find_linked_prs(story['id'])
            story_data['actual_metrics'] = {
                'pr_count': len(prs),
                'total_commits': sum(pr['commits_count'] for pr in prs),
                'files_changed': sum(pr['files_changed'] for pr in prs),
                'task_count': len(story.get('tasks', [])),
                'duration_days': self.calculate_duration(story)
            }

            # 4. Calculate actual points (simple heuristic)
            story_data['actual_points'] = self.calculate_actual_points(story_data)

            # 5. Store in simple database
            self.db.insert('story_history', story_data)

    def calculate_actual_points(self, story_data):
        """Simple rule-based actual points calculation"""
        metrics = story_data['actual_metrics']

        # Base points from task count (1 point per 2 tasks on average)
        task_points = metrics['task_count'] / 2

        # Adjust for code complexity (every 100 lines = 1 point)
        # This is a rough approximation - you'd need actual line counts
        code_points = metrics['files_changed'] * 0.5

        # Adjust for duration (1 week = 5 points for average team)
        duration_points = metrics['duration_days'] / 7 * 5

        # Take the average, but at least 1 point
        actual_points = max(1, round((task_points + code_points + duration_points) / 3))

        return actual_points
```

### Database Schema (Keep it Simple):
```sql
CREATE TABLE story_history (
    id INTEGER PRIMARY KEY,
    story_id INTEGER UNIQUE,
    title TEXT,
    description TEXT,
    estimated_points INTEGER,
    actual_points INTEGER,
    error_ratio REAL,  -- actual/estimated
    created_date TEXT,
    completed_date TEXT,
    team_id TEXT,
    tags TEXT,  -- JSON array
    pr_count INTEGER,
    task_count INTEGER,
    duration_days INTEGER
);

CREATE TABLE team_stats (
    team_id TEXT PRIMARY KEY,
    total_stories INTEGER,
    avg_error_ratio REAL,
    velocity INTEGER,  -- Average points per sprint
    last_updated TEXT
);
```

## Phase 2: Simple Learning Engine (Week 3-4)

### Core Learning Logic:
```python
# story_size/core/simple_learner.py
class SimpleStoryLearner:
    """Simple but effective learning engine"""

    def __init__(self, db_connection):
        self.db = db_connection

    def estimate_story(self, title, description, team_id=None):
        """Get an estimate using simple but effective methods"""

        # 1. Find similar stories (simple text similarity)
        similar_stories = self.find_similar_stories(title, description)

        # 2. Get team average if available
        team_avg = self.get_team_average(team_id)

        # 3. Calculate estimate
        if similar_stories:
            # Weighted average: 70% similar stories, 30% team average
            estimate = (sum(s['actual_points'] for s in similar_stories[:5]) / len(similar_stories[:5]) * 0.7 +
                       team_avg * 0.3)
        else:
            # No similar stories - use team average
            estimate = team_avg

        # 4. Apply team calibration
        if team_id:
            calibration = self.get_team_calibration(team_id)
            estimate = estimate * calibration

        return {
            'estimate': max(1, round(estimate)),
            'confidence': self.calculate_confidence(similar_stories, team_id),
            'similar_stories': similar_stories[:3],
            'team_average': team_avg
        }

    def find_similar_stories(self, title, description, limit=5):
        """Find similar stories using simple keyword matching"""
        # Combine title and description
        full_text = f"{title} {description}".lower()

        # Extract important keywords (remove common words)
        keywords = self.extract_keywords(full_text)

        # Query database for stories with matching keywords
        query = """
        SELECT * FROM story_history
        WHERE title LIKE ? OR description LIKE ?
        ORDER BY completed_date DESC
        LIMIT ?
        """

        similar = []
        for keyword in keywords[:3]:  # Check top 3 keywords
            pattern = f"%{keyword}%"
            results = self.db.execute(query, (pattern, pattern, limit)).fetchall()

            for result in results:
                # Calculate simple similarity score
                score = self.calculate_similarity(full_text, result['title'], result['description'])
                if score > 0.3:  # Minimum similarity threshold
                    similar.append({
                        'story_id': result['story_id'],
                        'title': result['title'],
                        'estimated': result['estimated_points'],
                        'actual': result['actual_points'],
                        'similarity': score
                    })

        # Sort by similarity and return top matches
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:limit]

    def get_team_calibration(self, team_id):
        """Calculate team-specific calibration factor"""
        stats = self.db.execute(
            "SELECT avg_error_ratio FROM team_stats WHERE team_id = ?",
            (team_id,)
        ).fetchone()

        if stats:
            # If team consistently overestimates (ratio < 1), adjust down
            # If team consistently underestimates (ratio > 1), adjust up
            return 1.0 / stats['avg_error_ratio']

        return 1.0  # No calibration needed

    def learn_from_outcome(self, story_id, actual_points):
        """Update learning from actual outcome"""
        # Update the story with actual points
        self.db.execute(
            "UPDATE story_history SET actual_points = ?, error_ratio = ? WHERE story_id = ?",
            (actual_points, actual_points / self.get_estimated_points(story_id), story_id)
        )

        # Update team stats
        self.update_team_stats(self.get_story_team(story_id))
```

## Phase 3: Team Calibration (Week 5-6)

### Simple Team Patterns:
```python
# story_size/core/team_calibration.py
class TeamCalibration:
    """Understand and adjust for team patterns"""

    def analyze_team_patterns(self, team_id):
        """Identify team-specific estimation patterns"""

        # Get team's completed stories
        stories = self.db.execute(
            "SELECT * FROM story_history WHERE team_id = ? AND actual_points IS NOT NULL",
            (team_id,)
        ).fetchall()

        if len(stories) < 5:
            return {"message": "Need more data (minimum 5 stories)"}

        patterns = {
            'total_stories': len(stories),
            'average_error': sum(s['error_ratio'] for s in stories) / len(stories),
            'overestimate_frequency': sum(1 for s in stories if s['error_ratio'] < 0.8) / len(stories),
            'underestimate_frequency': sum(1 for s in stories if s['error_ratio'] > 1.2) / len(stories),
            'size_patterns': self.analyze_by_size(stories),
            'tag_patterns': self.analyze_by_tags(stories)
        }

        # Generate insights
        insights = []
        if patterns['average_error'] < 0.9:
            insights.append("Team tends to overestimate (average 10% too high)")
        elif patterns['average_error'] > 1.1:
            insights.append("Team tends to underestimate (average 10% too low)")
        else:
            insights.append("Team estimates are quite accurate")

        if patterns['overestimate_frequency'] > 0.3:
            insights.append("Consider reducing estimates for similar work")

        return {
            'patterns': patterns,
            'insights': insights,
            'recommendation': self.get_calibration_recommendation(patterns)
        }

    def get_calibration_recommendation(self, patterns):
        """Simple recommendation based on patterns"""
        error = patterns['average_error']

        if error < 0.85:
            return f"Reduce estimates by {round((1-error)*100)}%"
        elif error > 1.15:
            return f"Increase estimates by {round((error-1)*100)}%"
        else:
            return "Current estimates are accurate enough"
```

## Phase 4: Continuous Improvement (Week 7-8)

### Simple Feedback Loop:
```python
# story_size/core/feedback.py
class ContinuousImprovement:
    """Learn continuously with minimal complexity"""

    def weekly_improvement(self):
        """Simple weekly learning routine"""

        # 1. Collect this week's completed stories
        new_completions = self.get_weekly_completions()

        # 2. Update models
        for story in new_completions:
            self.learner.learn_from_outcome(story['id'], story['actual'])

        # 3. Check if accuracy is improving
        recent_accuracy = self.calculate_recent_accuracy(30)  # Last 30 days
        older_accuracy = self.calculate_recent_accuracy(90)   # Previous 30-90 days

        # 4. Simple alerting
        if recent_accuracy < older_accuracy * 0.9:  # 10% drop
            self.send_alert("Estimation accuracy decreased this month")

        # 5. Update team calibrations
        self.update_all_team_calibrations()

    def generate_monthly_report(self):
        """Simple monthly insights for the team"""

        report = {
            'month': datetime.now().strftime("%Y-%m"),
            'total_stories': self.count_stories_this_month(),
            'average_accuracy': self.calculate_monthly_accuracy(),
            'most_acurate_team': self.find_most_accurate_team(),
            'biggest_improvement': self.find_biggest_improvement(),
            'recommendations': self.generate_recommendations()
        }

        # Send to team (email, Slack, or display in dashboard)
        self.send_monthly_report(report)
```

## Integration with Existing Tool

### Minimal Changes to story-size:
```python
# Add to story_size/core/platform_ai_client.py
class PlatformAwareAIClient:
    def __init__(self, config_data):
        # ... existing code ...
        self.learner = SimpleStoryLearner(config_data.get('learning_db'))

    async def get_complete_analysis(self, doc_summary, code_analysis):
        # Try to get AI estimate (existing logic)
        ai_estimate = await self.get_ai_analysis(doc_summary, code_analysis)

        # But also get learning-based estimate
        title = extract_title_from_doc(doc_summary)
        learning_estimate = self.learner.estimate_story(
            title,
            doc_summary,
            team_id=extract_team_from_context(doc_summary)
        )

        # Use learning estimate if we have enough confidence
        if learning_estimate['confidence'] > 0.7:
            return {
                'platform_detection': ai_estimate.platform_detection,
                'story_points': learning_estimate['estimate'],
                'confidence': learning_estimate['confidence'],
                'method': 'learning_based',
                'similar_stories': learning_estimate['similar_stories'],
                'explanation': f"Based on {len(learning_estimate['similar_stories'])} similar stories"
            }

        # Fall back to AI estimate
        return ai_estimate
```

## What This Actually Gives You:

1. **Week 1-2**: Start collecting real data
2. **Week 3-4**: Basic similarity matching working
3. **Week 5-6**: Team-specific adjustments
4. **Week 7-8**: Continuous improvement loop

### Expected Results:
- **20-30% improvement** in estimation accuracy after 2 months
- **Team insights** about estimation patterns
- **Confidence scores** based on historical data
- **Minimal maintenance** - no complex ML to manage

### What You DON'T Get:
- Complex ML models
- Real-time learning (daily/weekly is fine)
- Advanced pattern recognition
- Automated everything

### When to Consider More Complexity:
- If simple approach isn't improving accuracy
- If you have >1000 stories to learn from
- If teams have wildly different patterns
- If you need to estimate multiple project types

## The Bottom Line

Start simple. The basic approach of "look at similar past work" and "adjust for team patterns" captures 80% of the value with 10% of the complexity. Add sophistication ONLY when you prove you need it.

Remember: The goal is better estimation, not building a fancy AI system. Simple statistical methods often outperform complex ML for this use case.