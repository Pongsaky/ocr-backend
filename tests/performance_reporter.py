"""
Performance reporting and analysis system for OCR API testing.
Generates comprehensive reports with metrics, charts, and historical tracking.
"""

import json
import sqlite3
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import base64
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


@dataclass
class TestMetrics:
    """Individual test metrics."""
    test_name: str
    timestamp: datetime
    response_times: List[float]
    success_count: int
    error_count: int
    total_requests: int
    duration: float
    errors: List[str]
    metadata: Dict[str, Any]
    
    # New fields for real performance tracking
    creation_times: List[float] = None  # Task creation times
    processing_times: List[float] = None  # Actual OCR processing times
    queue_wait_times: List[float] = None  # Time waiting in queue


@dataclass
class PerformanceSummary:
    """Performance summary statistics."""
    avg_response_time: float
    median_response_time: float
    percentile_95_response_time: float
    percentile_99_response_time: float
    min_response_time: float
    max_response_time: float
    success_rate: float
    error_rate: float
    throughput: float  # requests per second
    total_requests: int
    total_duration: float
    
    # New fields for real performance breakdown
    avg_creation_time: float = 0
    avg_processing_time: float = 0
    avg_queue_wait_time: float = 0
    real_throughput: float = 0  # Based on actual processing time


class PerformanceReporter:
    """Comprehensive performance reporting system."""
    
    def __init__(self, db_path: Optional[str] = None, reports_dir: Optional[str] = None):
        """Initialize the performance reporter."""
        self.db_path = db_path or "tests/performance_data.db"
        self.reports_dir = Path(reports_dir or "tests/performance_reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Current session metrics
        self.current_metrics: List[TestMetrics] = []
        
    def _init_database(self):
        """Initialize SQLite database for historical tracking."""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    deployment_url TEXT,
                    response_times TEXT,  -- JSON array
                    success_count INTEGER,
                    error_count INTEGER,
                    total_requests INTEGER,
                    duration REAL,
                    errors TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    summary_stats TEXT  -- JSON object
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_runs(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_name ON performance_runs(test_name)
            """)
            
            conn.commit()
    
    def record_test_metrics(self, 
                           test_name: str,
                           response_times: List[float],
                           success_count: int,
                           error_count: int,
                           duration: float,
                           errors: List[str] = None,
                           metadata: Dict[str, Any] = None,
                           creation_times: List[float] = None,
                           processing_times: List[float] = None,
                           queue_wait_times: List[float] = None) -> TestMetrics:
        """Record metrics for a single test."""
        metrics = TestMetrics(
            test_name=test_name,
            timestamp=datetime.now(timezone.utc),
            response_times=response_times,
            success_count=success_count,
            error_count=error_count,
            total_requests=success_count + error_count,
            duration=duration,
            errors=errors or [],
            metadata=metadata or {},
            creation_times=creation_times or [],
            processing_times=processing_times or [],
            queue_wait_times=queue_wait_times or []
        )
        
        self.current_metrics.append(metrics)
        return metrics
    
    def calculate_summary(self, metrics: TestMetrics) -> PerformanceSummary:
        """Calculate performance summary from metrics."""
        response_times = metrics.response_times
        
        if not response_times:
            return PerformanceSummary(
                avg_response_time=0,
                median_response_time=0,
                percentile_95_response_time=0,
                percentile_99_response_time=0,
                min_response_time=0,
                max_response_time=0,
                success_rate=0,
                error_rate=100.0,
                throughput=0,
                total_requests=metrics.total_requests,
                total_duration=metrics.duration
            )
        
        sorted_times = sorted(response_times)
        
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0
            index = int(p * len(data))
            return data[min(index, len(data) - 1)]
        
        success_rate = (metrics.success_count / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
        error_rate = (metrics.error_count / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
        throughput = metrics.total_requests / metrics.duration if metrics.duration > 0 else 0
        
        # Calculate timing breakdowns
        avg_creation_time = statistics.mean(metrics.creation_times) if metrics.creation_times else 0
        avg_processing_time = statistics.mean(metrics.processing_times) if metrics.processing_times else 0
        avg_queue_wait_time = statistics.mean(metrics.queue_wait_times) if metrics.queue_wait_times else 0
        
        # Calculate real throughput based on processing time
        real_throughput = 0
        if avg_processing_time > 0:
            real_throughput = 1 / avg_processing_time  # requests per second based on processing time
        
        return PerformanceSummary(
            avg_response_time=statistics.mean(response_times),
            median_response_time=statistics.median(response_times),
            percentile_95_response_time=percentile(sorted_times, 0.95),
            percentile_99_response_time=percentile(sorted_times, 0.99),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            success_rate=success_rate,
            error_rate=error_rate,
            throughput=throughput,
            total_requests=metrics.total_requests,
            total_duration=metrics.duration,
            avg_creation_time=avg_creation_time,
            avg_processing_time=avg_processing_time,
            avg_queue_wait_time=avg_queue_wait_time,
            real_throughput=real_throughput
        )
    
    def save_to_database(self, metrics: TestMetrics, deployment_url: str = ""):
        """Save metrics to database for historical tracking."""
        summary = self.calculate_summary(metrics)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance_runs 
                (timestamp, test_name, deployment_url, response_times, success_count, 
                 error_count, total_requests, duration, errors, metadata, summary_stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp.isoformat(),
                metrics.test_name,
                deployment_url,
                json.dumps(metrics.response_times),
                metrics.success_count,
                metrics.error_count,
                metrics.total_requests,
                metrics.duration,
                json.dumps(metrics.errors),
                json.dumps(metrics.metadata),
                json.dumps(asdict(summary))
            ))
            conn.commit()
    
    def get_historical_data(self, test_name: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical performance data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if test_name:
                cursor.execute("""
                    SELECT * FROM performance_runs 
                    WHERE test_name = ? AND timestamp > datetime('now', '-{} days')
                    ORDER BY timestamp DESC
                """.format(days), (test_name,))
            else:
                cursor.execute("""
                    SELECT * FROM performance_runs 
                    WHERE timestamp > datetime('now', '-{} days')
                    ORDER BY timestamp DESC
                """.format(days))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def create_chart(self, 
                    data: List[Tuple[str, float]], 
                    title: str, 
                    xlabel: str, 
                    ylabel: str,
                    chart_type: str = "line") -> Optional[str]:
        """Create a chart and return base64 encoded image."""
        if not MATPLOTLIB_AVAILABLE or not data:
            return None
        
        try:
            plt.figure(figsize=(10, 6))
            
            labels, values = zip(*data)
            
            if chart_type == "bar":
                plt.bar(labels, values)
                plt.xticks(rotation=45)
            else:  # line chart
                plt.plot(labels, values, marker='o')
                plt.xticks(rotation=45)
            
            plt.title(title)
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.tight_layout()
            
            # Save to bytes
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            
            # Encode to base64
            img_b64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()
            
            return img_b64
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            return None
    
    def generate_html_report(self, 
                           deployment_url: str = "",
                           include_historical: bool = True) -> str:
        """Generate comprehensive HTML report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate overall metrics
        total_requests = sum(m.total_requests for m in self.current_metrics)
        total_errors = sum(m.error_count for m in self.current_metrics)
        total_duration = sum(m.duration for m in self.current_metrics)
        
        overall_success_rate = ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 0
        
        # Generate test summaries
        test_summaries = []
        for metrics in self.current_metrics:
            summary = self.calculate_summary(metrics)
            test_summaries.append({
                'name': metrics.test_name,
                'summary': summary,
                'metrics': metrics
            })
        
        # Create charts
        charts = {}
        
        # Response time chart
        if self.current_metrics:
            response_time_data = [(m.test_name, self.calculate_summary(m).avg_response_time) 
                                 for m in self.current_metrics]
            charts['response_times'] = self.create_chart(
                response_time_data,
                "Average Response Times by Test",
                "Test Name",
                "Response Time (seconds)",
                "bar"
            )
        
        # Throughput chart
        if self.current_metrics:
            throughput_data = [(m.test_name, self.calculate_summary(m).throughput) 
                              for m in self.current_metrics]
            charts['throughput'] = self.create_chart(
                throughput_data,
                "Throughput by Test",
                "Test Name", 
                "Requests/Second",
                "bar"
            )
        
        # Historical comparison if available
        historical_chart = None
        if include_historical and self.current_metrics:
            historical_data = self.get_historical_data(days=7)
            if historical_data:
                # Group by date and calculate average response times
                daily_avg = defaultdict(list)
                for record in historical_data:
                    date = record['timestamp'][:10]  # Extract date part
                    summary_stats = json.loads(record['summary_stats'])
                    daily_avg[date].append(summary_stats['avg_response_time'])
                
                historical_chart_data = [(date, statistics.mean(times)) 
                                       for date, times in daily_avg.items()]
                historical_chart_data.sort()
                
                historical_chart = self.create_chart(
                    historical_chart_data[-7:],  # Last 7 days
                    "Response Time Trend (Last 7 Days)",
                    "Date",
                    "Average Response Time (seconds)"
                )
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR API Performance Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .section {{
            padding: 30px;
            border-bottom: 1px solid #eee;
        }}
        .section:last-child {{
            border-bottom: none;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .test-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .test-table th, .test-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .test-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .status-success {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-warning {{
            color: #ffc107;
            font-weight: bold;
        }}
        .status-error {{
            color: #dc3545;
            font-weight: bold;
        }}
        .chart-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .alert {{
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .alert-info {{
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }}
        .alert-warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 OCR API Performance Report</h1>
            <p>Generated on {timestamp}</p>
            {f'<p>Deployment: {deployment_url}</p>' if deployment_url else ''}
        </div>
        
        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_requests}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{overall_success_rate:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(self.current_metrics)}</div>
                    <div class="metric-label">Tests Executed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_duration:.1f}s</div>
                    <div class="metric-label">Total Duration</div>
                </div>
            </div>
            
            {self._generate_timing_breakdown_section()}
            
            
            {self._generate_alerts(overall_success_rate)}
        </div>
        
        <div class="section">
            <h2>📈 Performance Charts</h2>
            {self._generate_chart_html(charts)}
        </div>
        
        {self._generate_historical_section(historical_chart) if historical_chart else ''}
        
        <div class="section">
            <h2>🔍 Detailed Test Results</h2>
            <table class="test-table">
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Requests</th>
                        <th>Success Rate</th>
                        <th>Avg Response Time</th>
                        <th>95th Percentile</th>
                        <th>Creation Time</th>
                        <th>Processing Time</th>
                        <th>Real Throughput</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {self._generate_test_rows(test_summaries)}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Report generated by OCR API Performance Testing Suite</p>
            <p>For more information, see the test documentation</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def _generate_alerts(self, success_rate: float) -> str:
        """Generate alert sections based on performance."""
        alerts = []
        
        if success_rate < 90:
            alerts.append("""
                <div class="alert alert-warning">
                    <strong>⚠️ Performance Alert:</strong> Success rate below 90%. 
                    Consider investigating error causes and system performance.
                </div>
            """)
        
        if success_rate >= 95:
            alerts.append("""
                <div class="alert alert-info">
                    <strong>✅ Performance Good:</strong> Success rate above 95%. 
                    System is performing well under current load.
                </div>
            """)
        
        return ''.join(alerts)
    
    def _generate_timing_breakdown_section(self) -> str:
        """Generate timing breakdown section for real performance metrics."""
        if not self.current_metrics:
            return ""
        
        # Check if we have real performance data
        has_timing_breakdown = any(
            m.creation_times or m.processing_times or m.queue_wait_times 
            for m in self.current_metrics
        )
        
        if not has_timing_breakdown:
            return ""
        
        return f"""
        <div class="section">
            <h2>⏱️ Timing Breakdown Analysis</h2>
            <div class="alert alert-info">
                <strong>📊 Real Performance Metrics:</strong> This section shows the breakdown of actual OCR processing times, not just HTTP response times.
            </div>
            
            <div class="metrics-grid">
                {self._generate_timing_breakdown_cards()}
            </div>
        </div>
        """
    
    def _generate_timing_breakdown_cards(self) -> str:
        """Generate timing breakdown metric cards."""
        cards = []
        
        # Aggregate timing data across all tests
        all_creation_times = []
        all_processing_times = []
        all_queue_times = []
        
        for metrics in self.current_metrics:
            if metrics.creation_times:
                all_creation_times.extend(metrics.creation_times)
            if metrics.processing_times:
                all_processing_times.extend(metrics.processing_times)
            if metrics.queue_wait_times:
                all_queue_times.extend(metrics.queue_wait_times)
        
        # Average creation time
        if all_creation_times:
            avg_creation = statistics.mean(all_creation_times)
            cards.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_creation:.2f}s</div>
                    <div class="metric-label">Avg Task Creation</div>
                </div>
            """)
        
        # Average processing time
        if all_processing_times:
            avg_processing = statistics.mean(all_processing_times)
            cards.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_processing:.1f}s</div>
                    <div class="metric-label">Avg OCR Processing</div>
                </div>
            """)
        
        # Average queue wait time
        if all_queue_times:
            avg_queue = statistics.mean(all_queue_times)
            cards.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_queue:.1f}s</div>
                    <div class="metric-label">Avg Queue Wait</div>
                </div>
            """)
        
        # Real throughput
        if all_processing_times:
            real_throughput = 1 / statistics.mean(all_processing_times)
            cards.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{real_throughput:.2f}</div>
                    <div class="metric-label">Real Throughput (req/s)</div>
                </div>
            """)
        
        return ''.join(cards)
    
    def _generate_chart_html(self, charts: Dict[str, str]) -> str:
        """Generate HTML for charts."""
        html_parts = []
        
        for chart_name, chart_data in charts.items():
            if chart_data:
                html_parts.append(f"""
                    <div class="chart-container">
                        <img src="data:image/png;base64,{chart_data}" alt="{chart_name} chart">
                    </div>
                """)
        
        if not html_parts:
            html_parts.append("""
                <div class="alert alert-info">
                    <strong>📊 Charts:</strong> Chart generation requires matplotlib. 
                    Install with: pip install matplotlib
                </div>
            """)
        
        return ''.join(html_parts)
    
    def _generate_historical_section(self, historical_chart: str) -> str:
        """Generate historical trends section."""
        return f"""
        <div class="section">
            <h2>📅 Historical Trends</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{historical_chart}" alt="Historical trends chart">
            </div>
        </div>
        """
    
    def _generate_test_rows(self, test_summaries: List[Dict]) -> str:
        """Generate table rows for test results."""
        rows = []
        
        for test_data in test_summaries:
            summary = test_data['summary']
            
            # Determine status
            if summary.success_rate >= 95:
                status = '<span class="status-success">Excellent</span>'
            elif summary.success_rate >= 80:
                status = '<span class="status-warning">Good</span>'
            else:
                status = '<span class="status-error">Poor</span>'
            
            rows.append(f"""
                <tr>
                    <td>{test_data['name']}</td>
                    <td>{summary.total_requests}</td>
                    <td>{summary.success_rate:.1f}%</td>
                    <td>{summary.avg_response_time:.2f}s</td>
                    <td>{summary.percentile_95_response_time:.2f}s</td>
                    <td>{summary.avg_creation_time:.2f}s</td>
                    <td>{summary.avg_processing_time:.1f}s</td>
                    <td>{summary.real_throughput:.2f} req/s</td>
                    <td>{status}</td>
                </tr>
            """)
        
        return ''.join(rows)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON report for programmatic analysis."""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_tests': len(self.current_metrics),
                'total_requests': sum(m.total_requests for m in self.current_metrics),
                'total_errors': sum(m.error_count for m in self.current_metrics),
                'total_duration': sum(m.duration for m in self.current_metrics),
            },
            'tests': []
        }
        
        for metrics in self.current_metrics:
            summary = self.calculate_summary(metrics)
            report['tests'].append({
                'name': metrics.test_name,
                'timestamp': metrics.timestamp.isoformat(),
                'metrics': asdict(metrics),
                'summary': asdict(summary)
            })
        
        return report
    
    def save_reports(self, 
                    deployment_url: str = "",
                    filename_prefix: str = "performance_report") -> Dict[str, str]:
        """Save all report formats and return file paths."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to database
        for metrics in self.current_metrics:
            self.save_to_database(metrics, deployment_url)
        
        # Generate reports
        html_report = self.generate_html_report(deployment_url)
        json_report = self.generate_json_report()
        
        # Save files
        html_path = self.reports_dir / f"{filename_prefix}_{timestamp}.html"
        json_path = self.reports_dir / f"{filename_prefix}_{timestamp}.json"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, default=str)
        
        return {
            'html': str(html_path),
            'json': str(json_path)
        }
    
    def clear_current_metrics(self):
        """Clear current session metrics."""
        self.current_metrics.clear()