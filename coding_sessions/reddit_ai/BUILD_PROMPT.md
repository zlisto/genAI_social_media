# AI-Agent Reddit Simulator - Build Prompt

Build a React application called "AI-Agent Reddit Simulator" that simulates a Reddit-like discussion forum powered by AI agents. Each agent has a unique personality and can post, reply, or like content in an automated simulation.

## Environment Setup

**IMPORTANT:** I already have a `.env` file with the OpenAI API key configured. Use `process.env.REACT_APP_OPENAI_API_KEY` and `process.env.REACT_APP_MODEL` (defaults to 'gpt-5-nano' if not set).

## Core Architecture

### File Structure
- `src/App.js` - Main React component with all logic
- `src/App.css` - Reddit dark theme styling (#030303 background, #FF4500 accents)
- `src/aiService.js` - OpenAI API integration
- `src/index.js` - Entry point
- `public/prompt_action.txt` - Action prompt template
- `public/profiles.json` - Default agent profiles (load on mount)

### OpenAI API Integration

**CRITICAL:** Use the official `openai` npm package (not fetch). Install with `npm install openai`.

The `aiService.js` must:
1. Import `OpenAI` from 'openai'
2. Create a singleton client with `dangerouslyAllowBrowser: true` (required for React)
3. Export `callOpenAI(prompt, isJson = false)` function
4. Use `max_completion_tokens: 10000` (NOT `max_tokens`)
5. **DO NOT use `temperature` parameter** - the model doesn't support it
6. When `isJson = true`, set `response_format: { type: "json_object" }`
7. Access content via `completion.choices[0]?.message?.content`
8. Handle errors gracefully and log full response structure for debugging

### State Management

**Required State:**
- `agents` - Array of {id, name, bio, color}
- `posts` - Array of {id, author, content, likes, parentId, type, timestamp}
- `isRunning` - Boolean for simulation state
- `topic` - String (default: "Robert Downey Jr. as Dr. Doom is a Multiverse glitch to distract us from the fact that the MCU is dying.")
- `logs` - Array of log strings for system monitor
- `responses` - Array of saved OpenAI responses
- `isMonitorCollapsed` - Boolean for collapsible monitor
- `activeTab` - 'agents' or 'feed'

**Required Refs:**
- `postIdCounter` - Counter starting at 1
- `lastAgentRef` - Tracks last agent who acted (prevents consecutive actions)
- `fileHandleRef` - For File System Access API

### The Main Loop

**CRITICAL LOOP STRUCTURE:** The app runs ONE simple sequential loop when `isRunning` is true:

1. **Read feed** - Format current posts into text
2. **Select agent** - Uniformly random (excluding last agent)
3. **Select action** - Call OpenAI with action prompt (JSON mode)
4. **Update feed** - Parse JSON and apply action
5. **Sleep 5 seconds** - Wait before next iteration
6. **Repeat**

**IMPORTANT LOOP DETAILS:**
- Use `useEffect` with dependencies `[isRunning, agents, posts, topic]`
- Use `let cancelled = false` flag for cleanup
- The loop MUST wait for each OpenAI call to complete before proceeding
- After each iteration, sleep exactly 5 seconds (`await new Promise(resolve => setTimeout(resolve, 5000))`)
- Log "Sleeping for 5 seconds..." to system monitor before sleep
- Handle first post separately (random agent, then sleep 5s before entering main loop)
- On error, log error and sleep 5s before retrying

### Agent Selection

- **Uniform random selection** (no AI selector)
- Exclude `lastAgentRef.current` from selection
- If only one agent exists, they can still act (fallback)
- Log: "Winner: [name] selected (random)"

### Action Processing

**Action Prompt:**
- Fetch `prompt_action.txt` from `/public`
- Replace placeholders: `{name}`, `{bio}`, `{topic}`, `{feed}`
- Call OpenAI with `callOpenAI(actionPrompt, true)` - **MUST use JSON mode**

**Action JSON Format:**
```json
{
  "action": "post" | "reply" | "like",
  "content": "text content",
  "targetId": ID_OR_NULL
}
```

**Action Processing:**
- Parse JSON (handle markdown code blocks, extract JSON object)
- Convert `targetId` to Number (critical for matching)
- **Post**: Create new post with `parentId: null`
- **Reply**: Create reply with `parentId: Number(action.targetId)`
- **Like**: Increment likes on post with matching ID
- Update `lastAgentRef.current` after any action
- Log action to system monitor

### Feed Formatting

Format feed as text string:
```
[ID] AuthorName (color): Content [Likes: N](Reply to X)
```

### UI Components

**Tab 1: Agent Lab**
- Left: Form (name input, bio textarea, create button)
- Right: Grid of agent cards with avatar (colored circle), name, bio, delete button
- Assign colors from array: `['#FF4500', '#FF6B6B', '#4ECDC4', ...]`

**Tab 2: The Simulation**
- Header: Topic input (disabled when running), Start/Stop button
- Feed: Reddit-style cards
  - Username in agent's color
  - Post ID, content, likes, timestamp
  - Replies indented 30px with vertical line
  - Recursive rendering (replies can have replies)

**System Monitor (Fixed Bottom)**
- Collapsible header with ▲/▼ button
- Download button (shows count)
- Scrollable log area (monospace font)
- Height: 400px (collapsed: auto)
- Log format: `[timestamp] emoji message`

### Default Agents

Load from `public/profiles.json` on mount:
- Fetch `/profiles.json`
- Parse JSON array
- Create agents with colors assigned sequentially
- Log success/failure

### Response Saving

After each iteration, save to JSON file:
- Structure: `{timestamp, iteration, selector: {method, prompt, response, selectedAgent}, action: {prompt, response, agent}}`
- Use File System Access API (`showSaveFilePicker`) if available
- Fallback to download link
- Auto-save after each iteration
- File: `openai-responses.json`

### Critical Edge Cases

1. **Type Mismatch:** `targetId` from JSON is string, post IDs are numbers - MUST convert with `Number()`
2. **Reply Matching:** Use `Number(post.parentId) === Number(postId)` for comparison
3. **No Consecutive Actions:** Track `lastAgentRef.current` and exclude from selection
4. **Empty Feed:** Handle first post separately before main loop
5. **Stop Button:** Must properly cancel loop using `cancelled` flag
6. **JSON Parsing:** Extract JSON from markdown code blocks or plain text
7. **Error Handling:** Sleep 5s on error, don't crash loop
8. **Monitor Updates:** Only update when logs change (not every render)

### Styling Requirements

- Reddit dark theme: `#030303` background, `#D7DADC` text, `#FF4500` accents
- Fixed system monitor at bottom (400px height)
- Main content padding-bottom: 420px (adjusts when monitor collapsed)
- Responsive design for mobile
- Smooth transitions for collapse/expand

### System Monitor Logs

Log these events:
- Agent creation/deletion
- Simulation start/stop
- Agent selection
- Agent thinking
- Actions (post/reply/like)
- Errors
- Sleeping periods

### Testing Checklist

- [ ] Agents load from profiles.json on mount
- [ ] Can create/delete agents
- [ ] Simulation starts and runs loop
- [ ] Each iteration waits for OpenAI response
- [ ] Sleeps 5 seconds between iterations
- [ ] No agent acts twice in a row
- [ ] Replies show under correct parent posts
- [ ] Likes increment correctly
- [ ] Stop button works immediately
- [ ] System monitor updates only on log changes
- [ ] Monitor collapses/expands smoothly
- [ ] JSON responses save correctly
- [ ] Type conversions work (string to number for IDs)

## Key Implementation Notes

- **DO NOT** use `setInterval` - use async/await loop in useEffect
- **DO NOT** include `temperature` in OpenAI params
- **DO** use `max_completion_tokens` (not `max_tokens`)
- **DO** convert all `targetId` values to numbers
- **DO** wait for each OpenAI call before proceeding
- **DO** handle JSON extraction from various formats
- **DO** track last agent to prevent consecutive actions
- **DO** save responses after each iteration

Build this step by step, ensuring the loop runs sequentially and waits for all async operations before continuing.
