# Load Testing

## Quick Start
```bash
# Start the API
docker-compose up -d

# Run load test (50 users, 5 minute duration)
cd api
python tests/load/run_load_test.py

# Or with custom parameters
python tests/load/run_load_test.py --users 100 --run-time 10m
```

## Interactive Mode
```bash
cd api
locust -f tests/load/locustfile.py --host http://localhost:8000
# Open http://localhost:8089 in browser
```

## Performance Targets

| Metric | Target | Baseline |
|--------|--------|----------|
| Concurrent Users | 50+ | - |
| P95 Response Time | <1s | - |
| Error Rate | <1% | - |
| Requests/sec | 100+ | - |

## Test Scenarios

1. **DefensePMUser**: Simulates typical user behavior
   - List programs (50%)
   - Create/read programs (30%)
   - Create activities (20%)

2. **HeavyLoadUser**: Stress testing with expensive operations
   - Monte Carlo simulations
   - Large program operations

## Reports

Load test reports are saved to `tests/load/reports/`:
- `load_test_YYYYMMDD_HHMMSS.html` - Interactive HTML report
- `load_test_YYYYMMDD_HHMMSS_stats.csv` - Statistics CSV
- `load_test_YYYYMMDD_HHMMSS_failures.csv` - Failure details
- `load_test_YYYYMMDD_HHMMSS_stats_history.csv` - Time-series data

## CLI Options

```bash
python tests/load/run_load_test.py [OPTIONS]

Options:
  --host TEXT        Target API URL (default: http://localhost:8000)
  --users INTEGER    Number of concurrent users (default: 50)
  --spawn-rate INT   Users to spawn per second (default: 5)
  --run-time TEXT    Test duration, e.g., 5m, 1h (default: 5m)
```

## Interpreting Results

### Response Times
- **P50 (Median)**: Typical user experience
- **P95**: 95% of requests complete within this time
- **P99**: Tail latency, important for worst-case scenarios

### Key Metrics to Watch
- **RPS (Requests/sec)**: Throughput capacity
- **Failure Rate**: Should be <1% under normal load
- **Response Time Distribution**: Look for outliers
