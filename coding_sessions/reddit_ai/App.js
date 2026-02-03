import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import { callOpenAI } from './aiService';

function App() {
  const [activeTab, setActiveTab] = useState('agents');
  const [agents, setAgents] = useState([]);
  const [posts, setPosts] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [topic, setTopic] = useState('Robert Downey Jr. as Dr. Doom is a Multiverse glitch to distract us from the fact that the MCU is dying.');
  const [agentName, setAgentName] = useState('');
  const [agentBio, setAgentBio] = useState('');
  const [logs, setLogs] = useState([]);
  const [responses, setResponses] = useState([]);
  const [isMonitorCollapsed, setIsMonitorCollapsed] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const postIdCounter = useRef(1);
  const lastAgentRef = useRef(null);
  const postsRef = useRef([]);
  
  // Keep ref in sync with posts state (separate from main loop)
  useEffect(() => {
    postsRef.current = posts;
  }, [posts]);

  const colors = [
    '#FF4500', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
    '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739'
  ];

  const addLog = useCallback((message, emoji = '📝') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${timestamp}] ${emoji} ${message}`]);
  }, []);

  const playDingSound = () => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800; // Nice ding frequency
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
      console.log('Could not play sound:', error);
    }
  };

  const addNotification = (agentName, actionType) => {
    const notification = {
      id: Date.now(),
      agentName,
      actionType,
      timestamp: new Date().toLocaleTimeString()
    };
    setNotifications(prev => [notification, ...prev].slice(0, 10)); // Keep last 10
  };

  // Load default agents from profiles.json on mount
  useEffect(() => {
    const loadDefaultAgents = async () => {
      try {
        const response = await fetch('/profiles.json');
        if (!response.ok) {
          console.log('No profiles.json found, starting with empty agents');
          return;
        }
        
        const profiles = await response.json();
        if (Array.isArray(profiles) && profiles.length > 0) {
          const loadedAgents = profiles.map((profile, index) => ({
            id: Date.now() + index,
            name: profile.name,
            bio: profile.bio,
            color: colors[index % colors.length]
          }));
          
          setAgents(loadedAgents);
          const timestamp = new Date().toLocaleTimeString();
          setLogs(prev => [...prev, `[${timestamp}] 📥 Loaded ${loadedAgents.length} default agents from profiles.json`]);
        }
      } catch (error) {
        console.error('Error loading profiles:', error);
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [...prev, `[${timestamp}] ⚠️ Failed to load default agents`]);
      }
    };

    loadDefaultAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  const createAgent = () => {
    if (!agentName.trim() || !agentBio.trim()) {
      alert('Please fill in both name and bio');
      return;
    }

    const color = colors[agents.length % colors.length];
    const newAgent = {
      id: Date.now(),
      name: agentName,
      bio: agentBio,
      color: color
    };

    setAgents(prev => [...prev, newAgent]);
    setAgentName('');
    setAgentBio('');
    addLog(`Agent "${newAgent.name}" created`, '✨');
  };

  const deleteAgent = (id) => {
    setAgents(prev => prev.filter(agent => agent.id !== id));
    addLog('Agent deleted', '🗑️');
  };

  const fetchPromptTemplate = async (filename) => {
    try {
      const response = await fetch(`/${filename}`);
      if (!response.ok) throw new Error('Failed to fetch template');
      return await response.text();
    } catch (error) {
      console.error('Error fetching template:', error);
      throw error;
    }
  };

  const formatFeed = useCallback(() => {
    if (posts.length === 0) return 'No posts yet.';
    return posts.map(post => {
      const author = agents.find(a => a.name === post.author);
      const authorColor = author ? author.color : '#D7DADC';
      return `[${post.id}] ${post.author} (${authorColor}): ${post.content} [Likes: ${post.likes}]${post.parentId ? ` (Reply to ${post.parentId})` : ''}`;
    }).join('\n');
  }, [posts, agents]);


  const processAction = useCallback((agent, actionResponse) => {
      let jsonStr = '';
      try {
        // Try to parse JSON from the response
        jsonStr = actionResponse.trim();
        console.log('=== PROCESSING ACTION ===');
        console.log('Agent:', agent.name);
        console.log('Initial response:', jsonStr);
        
        // Extract JSON if it's wrapped in markdown code blocks
        const jsonMatch = jsonStr.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
        if (jsonMatch) {
          jsonStr = jsonMatch[1];
          console.log('Extracted from code block:', jsonStr);
        }

        // Extract JSON object if it's in the middle of text
        const jsonObjectMatch = jsonStr.match(/\{[\s\S]*\}/);
        if (jsonObjectMatch) {
          jsonStr = jsonObjectMatch[0];
          console.log('Extracted JSON object:', jsonStr);
        }

        console.log('Final JSON string to parse:', jsonStr);
        const action = JSON.parse(jsonStr);
        console.log('Parsed action:', action);

        if (action.action === 'like' && action.targetId) {
          const targetId = Number(action.targetId);
          setPosts(prev => {
            const updated = prev.map(post => 
              post.id === targetId 
                ? { ...post, likes: post.likes + 1 }
                : post
            );
            postsRef.current = updated;
            return updated;
          });
          addLog(`${agent.name} liked post ${targetId}`, '👍');
          lastAgentRef.current = agent.name;
        } else if (action.action === 'post' && action.content) {
          const newPost = {
            id: postIdCounter.current++,
            author: agent.name,
            content: action.content,
            likes: 0,
            parentId: null,
            type: 'post',
            timestamp: Date.now()
          };
          setPosts(prev => {
            const updated = [...prev, newPost];
            postsRef.current = updated;
            return updated;
          });
          addLog(`${agent.name} posted: "${action.content.substring(0, 50)}..."`, '📮');
          playDingSound();
          addNotification(agent.name, 'posted');
          lastAgentRef.current = agent.name;
        } else if (action.action === 'reply' && action.content && action.targetId) {
          const parentId = Number(action.targetId);
          const newReply = {
            id: postIdCounter.current++,
            author: agent.name,
            content: action.content,
            likes: 0,
            parentId: parentId,
            type: 'reply',
            timestamp: Date.now()
          };
          setPosts(prev => {
            const updated = [...prev, newReply];
            postsRef.current = updated;
            return updated;
          });
          addLog(`${agent.name} replied to post ${parentId}`, '💬');
          playDingSound();
          addNotification(agent.name, 'replied');
          lastAgentRef.current = agent.name;
        } else {
          addLog(`Invalid action format from ${agent.name}`, '⚠️');
        }
      } catch (error) {
        addLog(`Failed to parse action from ${agent.name}: ${error.message}`, '❌');
        console.error('=== ACTION PARSING ERROR ===');
        console.error('Error:', error);
        console.error('Error message:', error.message);
        console.error('Raw response:', actionResponse);
        console.error('Response length:', actionResponse?.length);
        console.error('Attempted JSON string:', jsonStr || 'N/A');
        console.error('Full error stack:', error.stack);
      }
  }, [addLog]);

  const saveIterationResponse = useCallback(async (selectorPrompt, selectorResponse, actionPrompt, actionResponse, agentName) => {
    setResponses(prev => {
      const iteration = {
        timestamp: new Date().toISOString(),
        iteration: prev.length + 1,
        selector: {
          method: selectorResponse === 'random_selection' ? 'random' : 'ai',
          prompt: selectorPrompt || 'N/A (random selection)',
          response: selectorResponse,
          selectedAgent: agentName
        },
        action: {
          prompt: actionPrompt,
          response: actionResponse,
          agent: agentName
        }
      };
      
      const updated = [...prev, iteration];
      
      // Save to project root using File System Access API
      const saveToRoot = async () => {
        try {
          if ('showSaveFilePicker' in window) {
            // Modern File System Access API
            const handle = await window.showSaveFilePicker({
              suggestedName: 'openai-responses.json',
              types: [{
                description: 'JSON files',
                accept: { 'application/json': ['.json'] }
              }]
            });
            const writable = await handle.createWritable();
            await writable.write(JSON.stringify(updated, null, 2));
            await writable.close();
          } else {
            // Fallback: try to save to project root via download
            // This will prompt user to save, but they can navigate to project root
            const dataStr = JSON.stringify(updated, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'openai-responses.json';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
          }
        } catch (error) {
          // User cancelled or error - silently fail for auto-save
          console.log('Save cancelled or failed:', error);
        }
      };
      
      // Auto-save after each iteration
      saveToRoot();
      
      return updated;
    });
  }, []);

  // Simple loop: Read feed -> Select agent -> Select action -> Update feed -> Sleep 5s -> Repeat
  useEffect(() => {
    if (!isRunning || agents.length === 0) {
      return;
    }

    let cancelled = false;

    const loop = async () => {
      // Handle first post (check ref to avoid dependency issues)
      if (postsRef.current.length === 0) {
        const randomAgent = agents[Math.floor(Math.random() * agents.length)];
        const firstPost = {
          id: postIdCounter.current++,
          author: randomAgent.name,
          content: `Starting the discussion about "${topic}"...`,
          likes: 0,
          parentId: null,
          type: 'post',
          timestamp: Date.now()
        };
        setPosts([firstPost]);
        postsRef.current = [firstPost];
        lastAgentRef.current = randomAgent.name;
        addLog(`${randomAgent.name} made the first post`, '📮');
        addLog('Sleeping for 5 seconds...', '💤');
        await new Promise(resolve => setTimeout(resolve, 5000));
      }

      while (isRunning && !cancelled) {
        try {
          // 1. Read feed (use ref to get latest posts without causing re-renders)
          const currentPosts = postsRef.current;
          const feedText = currentPosts.length === 0 
            ? 'No posts yet.' 
            : currentPosts.map(post => {
                const author = agents.find(a => a.name === post.author);
                const authorColor = author ? author.color : '#D7DADC';
                return `[${post.id}] ${post.author} (${authorColor}): ${post.content} [Likes: ${post.likes}]${post.parentId ? ` (Reply to ${post.parentId})` : ''}`;
              }).join('\n');
          
          // 2. Select agent uniformly at random (excluding last one)
          const excludedAgentName = lastAgentRef.current;
          const availableAgents = excludedAgentName 
            ? agents.filter(a => a.name !== excludedAgentName)
            : agents;
          
          const winner = availableAgents.length > 0
            ? availableAgents[Math.floor(Math.random() * availableAgents.length)]
            : agents[Math.floor(Math.random() * agents.length)]; // Fallback if only one agent
          
          addLog(`Winner: ${winner.name} selected (random)`, '✨');

          // 3. Select action
          addLog(`${winner.name} is thinking...`, '✍️');
          const actionTemplate = await fetchPromptTemplate('prompt_action.txt');
          const actionPrompt = actionTemplate
            .replace('{name}', winner.name)
            .replace('{bio}', winner.bio)
            .replace('{topic}', topic || 'general discussion')
            .replace('{feed}', feedText);

          console.log('=== ACTION PROMPT ===');
          console.log(actionPrompt);
          const actionResponse = await callOpenAI(actionPrompt, true); // Use JSON mode
          console.log('=== ACTION RESPONSE ===');
          console.log('Raw response:', actionResponse);

          // 4. Update feed
          processAction(winner, actionResponse);
          lastAgentRef.current = winner.name;
          
          // Save responses (no selector prompt/response since we're using random selection)
          saveIterationResponse('', 'random_selection', actionPrompt, actionResponse, winner.name);

          // 5. Sleep 5 seconds
          if (isRunning && !cancelled) {
            addLog('Sleeping for 5 seconds...', '💤');
            await new Promise(resolve => setTimeout(resolve, 5000));
          }
        } catch (error) {
          addLog(`Error: ${error.message}`, '❌');
          console.error('Loop error:', error);
          // Sleep on error too
          if (isRunning && !cancelled) {
            addLog('Sleeping for 5 seconds after error...', '💤');
            await new Promise(resolve => setTimeout(resolve, 5000));
          }
        }
      }
    };

    loop();

    return () => {
      cancelled = true;
    };
  }, [isRunning, agents, topic, processAction, saveIterationResponse, addLog]);

  const toggleRunning = () => {
    if (!topic.trim() && !isRunning) {
      alert('Please enter a topic before starting the simulation');
      return;
    }
    const newRunningState = !isRunning;
    setIsRunning(newRunningState);
    if (newRunningState) {
      addLog('Simulation started', '🚀');
      setResponses([]); // Clear responses when starting new simulation
    } else {
      addLog('Simulation stopped', '⏸️');
    }
  };


  const getAgentColor = (agentName) => {
    const agent = agents.find(a => a.name === agentName);
    return agent ? agent.color : '#D7DADC';
  };

  const getReplies = (postId) => {
    // Ensure both are numbers for comparison (handle string/number mismatch)
    return posts.filter(post => post.parentId !== null && Number(post.parentId) === Number(postId));
  };

  const AgentCard = ({ agent, onDelete }) => {
    return (
      <div className="agent-card">
        <div className="agent-avatar" style={{ backgroundColor: agent.color }}>
          {agent.name.charAt(0).toUpperCase()}
        </div>
        <div className="agent-info">
          <h3 style={{ color: agent.color }}>{agent.name}</h3>
          <p>{agent.bio}</p>
        </div>
        <button 
          className="delete-agent"
          onClick={() => onDelete(agent.id)}
        >
          ×
        </button>
      </div>
    );
  };

  const renderPost = (post) => {
    const replies = getReplies(post.id);
    const agentColor = getAgentColor(post.author);

    return (
      <div key={post.id} className="post-card">
        <div className="post-header">
          <span className="username" style={{ color: agentColor }}>
            u/{post.author}
          </span>
          <span className="post-id">#{post.id}</span>
          {post.parentId && <span className="reply-indicator">↳ Reply to #{post.parentId}</span>}
        </div>
        <div className="post-content">{post.content}</div>
        <div className="post-footer">
          <span className="likes">👍 {post.likes}</span>
          <span className="timestamp">
            {new Date(post.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {replies.length > 0 && (
          <div className="replies-container">
            {replies.map(reply => renderPost(reply))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 AI-Agent Reddit Simulator</h1>
        <div className="tabs">
          <button 
            className={activeTab === 'agents' ? 'active' : ''}
            onClick={() => setActiveTab('agents')}
          >
            Agent Lab
          </button>
          <button 
            className={activeTab === 'feed' ? 'active' : ''}
            onClick={() => setActiveTab('feed')}
          >
            The Simulation
          </button>
        </div>
      </header>

      <main className="main-content">
        {activeTab === 'agents' && (
          <div className="agent-lab">
            <div className="agent-form-section">
              <h2>Create New Agent</h2>
              <div className="form-group">
                <label>Agent Name</label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g., TechEnthusiast42"
                />
              </div>
              <div className="form-group">
                <label>Personality/Bio</label>
                <textarea
                  value={agentBio}
                  onChange={(e) => setAgentBio(e.target.value)}
                  placeholder="e.g., A tech-savvy developer who loves discussing AI and programming..."
                  rows="4"
                />
              </div>
              <button className="create-button" onClick={createAgent}>
                ✨ Create Agent
              </button>
            </div>

            <div className="agents-grid-section">
              <h2>Active Agents ({agents.length})</h2>
              <div className="agents-grid">
                {agents.length === 0 ? (
                  <p className="empty-state">No agents yet. Create your first agent!</p>
                ) : (
                  agents.map(agent => (
                    <AgentCard 
                      key={agent.id} 
                      agent={agent} 
                      onDelete={deleteAgent}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'feed' && (
          <div className="feed-container">
            <div className="feed-header sticky">
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Enter discussion topic..."
                disabled={isRunning}
                className="topic-input"
              />
              <button 
                className={`toggle-button ${isRunning ? 'stop' : 'start'}`}
                onClick={toggleRunning}
              >
                {isRunning ? '⏸️ Stop' : '▶️ Start'}
              </button>
            </div>

            <div className="feed-layout">
              <div className="feed">
                {posts.length === 0 ? (
                  <div className="empty-feed">
                    <p>No posts yet. {agents.length === 0 ? 'Create agents first, then' : ''} Start the simulation to begin!</p>
                  </div>
                ) : (
                  posts
                    .filter(post => !post.parentId)
                    .map(post => renderPost(post))
                )}
              </div>
              
              <div className="notifications-panel">
                <h3>Recent Activity</h3>
                <div className="notifications-list">
                  {notifications.length === 0 ? (
                    <div className="empty-notifications">No activity yet</div>
                  ) : (
                    notifications.map(notif => {
                      const agent = agents.find(a => a.name === notif.agentName);
                      const agentColor = agent ? agent.color : '#D7DADC';
                      return (
                        <div key={notif.id} className="notification-item">
                          <span className="notification-name" style={{ color: agentColor }}>
                            {notif.agentName}
                          </span>
                          <span className="notification-action">
                            {notif.actionType}
                          </span>
                          <span className="notification-time">{notif.timestamp}</span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <div className={`system-monitor ${isMonitorCollapsed ? 'collapsed' : ''}`}>
        <div className="monitor-header">
          <div className="monitor-header-left">
            <button 
              onClick={() => setIsMonitorCollapsed(!isMonitorCollapsed)}
              className="collapse-btn"
              title={isMonitorCollapsed ? 'Expand monitor' : 'Collapse monitor'}
            >
              {isMonitorCollapsed ? '▼' : '▲'}
            </button>
            <span>System Monitor</span>
          </div>
        </div>
        {!isMonitorCollapsed && (
          <div className="monitor-logs">
            {logs.length === 0 ? (
              <div className="log-entry">Waiting for activity...</div>
            ) : (
              logs.slice(-50).map((log, index) => (
                <div key={index} className="log-entry">{log}</div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
