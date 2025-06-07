# WriteSense Agent

**WriteSense Agent** is an intelligent assistant designed to help people with disabilities create and work with documents. The agent coordinates multiple specialized sub-agents using a hierarchical architecture and responds in Vietnamese to provide accessible document creation support.

## 🎯 What This Does

- **Document Creation Support**: Help users write reports, diaries, and various documents
- **Vietnamese Language**: Always responds in Vietnamese for accessibility
- **Multi-Agent System**: Orchestrator coordinates specialized agents for different tasks
- **Disability-Friendly**: Simple, clear interactions with step-by-step guidance

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone the Project

```bash
git clone https://github.com/AI4LI-Language/write-sense-agent.git
cd write-sense-agent
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install project in development mode
pip install -e .
```

### Step 3: Configure API Keys

Copy the environment template and add your API keys:

```bash
cp env.template .env
```

Edit `.env` file and add your API keys:
```bash
# At minimum, you need one of these:
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Step 4: Test Basic Setup

```bash
python examples/basic_usage.py
```

You should see the agent respond in Vietnamese! 🎉

---

## 🐳 Run with Docker (Recommended)

### Step 1: Start Services

```bash
docker-compose up --build -d
```

or 

```bash
docker-compose up --build
```

This starts:
- **WriteSense Agent** on `http://localhost:8123`
- **PostgreSQL** database on port `5433`
- **Redis** cache on port `6379`

### Step 2: Test the API

```bash
# Check if service is running
curl http://localhost:8123/ok

# Chat with the agent
python chat_with_agent.py
```

### Step 3: Use the API

```bash
# Create a thread
curl -X POST http://localhost:8123/threads -H "Content-Type: application/json" -d '{}'

# Send a message (replace THREAD_ID with actual ID)
curl -X POST http://localhost:8123/threads/THREAD_ID/runs \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {"messages": [{"role": "user", "content": "Bạn có thể giúp gì cho tôi?"}]}
  }'
```

### API DOCS:

```bash
http://localhost:8123/docs
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────┐
│         Orchestrator Agent          │  ← GPT-4.1 (Powerful model)
│     (Coordination & Vietnamese)     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│       Document Retriever Agent      │  ← GPT-4o-mini (Fast model)
│        (Document Operations)        │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│           MCP Server               │
│    (Document Retrieval Tools)      │
└─────────────────────────────────────┘
```

**Key Features:**
- **Separate Models**: Orchestrator uses powerful model, sub-agents use fast models
- **Dynamic Delegation**: Automatically chooses right agent for each task
- **Vietnamese Output**: All responses in Vietnamese for accessibility
- **Disability Support**: Simple, clear, step-by-step guidance

---

## ⚙️ Configuration


### Environment Variables

```bash
# Orchestrator Model (Primary coordination)
ORCHESTRATOR_LLM_PROVIDER=openai
ORCHESTRATOR_LLM_MODEL=gpt-4o

# MCP Agents Model (Task execution)
MCP_AGENTS_LLM_PROVIDER=openai
MCP_AGENTS_LLM_MODEL=gpt-4o-mini

# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Adding New MCP Servers

1. **Create MCP Server** (in `mcp_servers/` directory)
2. **Add to Configuration** (automatically discovered)
3. **Restart System** (agents are created automatically)

The system automatically:
- Creates one agent per MCP server
- Generates dynamic delegation guidelines
- Updates orchestrator prompt with new capabilities

---

## 🧪 Testing Your Setup

### Test 1: Basic Response
```bash
python chat_with_agent.py
# Ask: "Xin chào"
# Expect: Vietnamese greeting response
```

### Test 2: Agent Capabilities
```bash
# Ask: "Bạn có thể làm gì?"
# Expect: Vietnamese description + delegation to document agent
```

### Test 3: Document Tasks
```bash
# Ask: "Giúp tôi viết một báo cáo"
# Expect: Step-by-step guidance in Vietnamese
```

---

## 🔧 Troubleshooting

### Common Issues

**1. API Key Errors**
```bash
# Check your .env file has the right keys
cat .env | grep API_KEY
```

**2. Docker Not Starting**
```bash
# Check Docker status
docker-compose ps

# View logs
docker logs write-sense-agent
```

**3. Agent Not Responding in Vietnamese**
```bash
# Check system prompt in logs
docker logs write-sense-agent | grep "Vietnamese"
```

**4. No Tool Calls/Delegation**
```bash
# Check MCP agent registration
docker logs write-sense-agent | grep "Registered agents"
```

### Getting Help

1. Check the logs: `docker logs write-sense-agent`
2. Verify environment: `docker-compose ps`
3. Test basic endpoints: `curl http://localhost:8123/ok`

---

## 📁 Project Structure

```
write-sense-agent/
├── src/write_sense_agent/
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   ├── orchestrator.py     # Main orchestrator agent
│   │   └── mcp_agent.py        # MCP agent wrapper
│   └── graph.py                # Agent graph creation
├── mcp_servers/
│   └── document_retriever.py   # Document MCP server
├── examples/
│   └── basic_usage.py          # Simple test script
├── docker-compose.yml          # Docker services
├── chat_with_agent.py          # Interactive chat client
├── env.template               # Environment template
└── README.md                  # This file
```

---

## 🎉 Next Steps

1. **Customize for Your Needs**: Modify system prompts in `config.py`
2. **Add More MCP Servers**: Create new servers in `mcp_servers/`
3. **Extend Capabilities**: Add new tools to existing servers
4. **Deploy to Production**: Use `langgraph deploy` for cloud deployment

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test: `python examples/basic_usage.py`
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Create Pull Request

---

**Built with LangGraph + MCP for accessible document creation** 🚀

*Designed specifically to help people with disabilities create and work with documents through simple, Vietnamese language interactions.*
