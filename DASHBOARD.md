# Instagram Debate Bot Dashboard

The dashboard provides a web interface for reviewing and managing AI-generated responses to Instagram comments.

## Features

- **Review Pending Responses**: View all responses that need human review
- **Approve/Reject**: Approve responses to post them to Instagram, or reject them with a reason
- **Edit Responses**: Modify generated responses before approving
- **Filter by Status**: View responses by pending, approved, rejected, or all
- **Citations Display**: See which article sections were cited in each response
- **Auto-refresh**: Dashboard automatically updates every 5 seconds

## Running the Dashboard

### Prerequisites

- Python 3.8+
- FastAPI and uvicorn installed (included in `requirements.txt`)

### Start the Dashboard

```bash
# Default port (5000) and host (127.0.0.1)
python dashboard.py

# Custom port via command line
python dashboard.py 8080

# Custom port and host via environment variables
DASHBOARD_PORT=3000 DASHBOARD_HOST=0.0.0.0 python dashboard.py
```

The dashboard will be available at `http://127.0.0.1:5000` (or your custom port/host).

You can also set `DASHBOARD_PORT` and `DASHBOARD_HOST` in your `.env` file for persistent configuration.

## Running Tests

The dashboard includes comprehensive UI tests using Playwright.

### Install Test Dependencies

```bash
# Install npm packages
npm install

# Install Playwright browsers
npx playwright install chromium
```

### Run Tests

```bash
# Run all tests
npm run test:ui

# Run tests with browser visible
npm run test:ui:headed

# Debug tests
npm run test:ui:debug
```

### Test Coverage

The test suite includes:

1. **Empty State Test**: Verifies dashboard shows empty state when no responses exist
2. **Display Pending Responses**: Tests that pending responses are displayed correctly
3. **Approve Response**: Tests the approval workflow
4. **Reject Response**: Tests rejection with reason
5. **Edit Response**: Tests editing and saving responses
6. **Filter by Status**: Tests filtering responses by different statuses
7. **Citations Display**: Tests that citations are properly displayed
8. **Validation Status**: Tests validation status display

## Dashboard Workflow

### For Manual Review Mode (auto_post_enabled = false)

1. The bot processes comments and generates responses
2. Responses are saved with status `pending_review` in `state/audit_log.json`
3. Open the dashboard to review pending responses
4. For each response:
   - **Approve**: Marks response as approved (can be posted by running main.py)
   - **Reject**: Marks as rejected with a reason (won't be posted)
   - **Edit**: Modify the response text before approving

### For Auto-Post Mode (auto_post_enabled = true)

The dashboard can still be used to:
- Review already-posted responses (approved status)
- View rejected responses and reasons
- Monitor the bot's activity

## State Files

The dashboard reads from and writes to:

- `state/audit_log.json` - Contains all generated responses with their status
- Uses the same state directory as the main bot application

## API Endpoints

The dashboard provides REST API endpoints:

- `GET /api/responses` - Get all responses
- `GET /api/responses/pending` - Get only pending responses
- `GET /api/responses/posted` - Get only posted responses (with `posted=true`)
- `POST /api/responses/{id}/approve` - Approve a response
- `POST /api/responses/{id}/reject` - Reject a response (with reason in body)
- `POST /api/responses/{id}/edit` - Edit a response (with text in body)

## Architecture

### Test Setup

The test infrastructure includes:

1. **Test Server** (`test_server.py`): 
   - Mock Instagram API endpoints
   - Mock OpenRouter/LLM API endpoints
   - Dashboard API and UI
   - Test data seeding endpoints

2. **Playwright Tests** (`e2e/dashboard.spec.js`):
   - Automated UI tests for all dashboard features
   - Uses Chromium browser for testing
   - Includes retry logic and screenshots on failure

3. **Playwright Config** (`playwright.config.js`):
   - Configures test environment
   - Automatically starts test server
   - Generates HTML reports

### Mock Servers

The test server includes mock implementations of:

1. **Mock Instagram API**:
   - `GET /mock-instagram/post/{post_id}` - Get post data
   - `GET /mock-instagram/comment/{comment_id}` - Get comment data
   - `POST /mock-instagram/comment/{comment_id}/reply` - Post reply
   - `POST /mock-instagram/webhook/trigger` - Trigger webhook (for testing)

2. **Mock OpenRouter API**:
   - `POST /mock-openrouter/api/v1/chat/completions` - Mock LLM responses
   - Returns appropriate responses for relevance checks and debate generation

## Development

### Running the Test Server

For development and testing:

```bash
python test_server.py
```

This starts the test server on port 5001 with:
- Dashboard UI
- Mock APIs
- Test data seeding endpoints

### File Structure

```
instagram_debater/
├── dashboard.py           # Production dashboard application
├── test_server.py        # Test server with mocks
├── e2e/
│   └── dashboard.spec.js # Playwright UI tests
├── playwright.config.js  # Playwright configuration
├── package.json          # npm dependencies
├── state/               # Bot state files (runtime)
│   └── audit_log.json  # Response audit log
└── test_state/         # Test state files (testing only)
```

## Security Notes

- The dashboard should only be accessible on localhost by default
- For production use over a network, add authentication
- Consider using HTTPS if exposing the dashboard externally
- The dashboard has read/write access to audit logs

## Troubleshooting

### Dashboard shows no responses

- Check that `state/audit_log.json` exists and contains entries
- Verify the bot has processed some comments
- Run the bot with manual review mode enabled

### Tests failing

- Ensure Python dependencies are installed: `pip install -r requirements.txt`
- Ensure Playwright is installed: `npx playwright install chromium`
- Check that port 5001 is available
- Try running tests in headed mode: `npm run test:ui:headed`

### Changes not appearing in dashboard

- The dashboard auto-refreshes every 5 seconds
- Try manually refreshing the browser
- Check browser console for JavaScript errors
