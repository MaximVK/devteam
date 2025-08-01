#!/bin/bash
# Setup agent workspace for development

echo "🔧 Setting up Agent Workspace"
echo "============================"

# Check if workspace directory exists
WORKSPACE_DIR="$HOME/dev/agent-workspace"
REPO_DIR="$WORKSPACE_DIR/devteam"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "Creating workspace directory..."
    mkdir -p "$WORKSPACE_DIR"
fi

# Clone repository if not exists
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning repository..."
    cd "$WORKSPACE_DIR"
    git clone https://github.com/MaximVK/devteam.git
    cd devteam
else
    echo "Repository already exists. Pulling latest changes..."
    cd "$REPO_DIR"
    git pull origin main
fi

# Configure git for agents
echo ""
echo "Configuring git for agents..."
git config user.name "DevTeam Agents"
git config user.email "agents@devteam.local"

# Install dependencies if needed
if [ -f "package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

if [ -f "web/frontend/package.json" ]; then
    echo "Installing frontend dependencies..."
    cd web/frontend
    npm install
    cd ../..
fi

# Create agent directories
echo ""
echo "Creating agent working directories..."
mkdir -p logs/agents
mkdir -p tmp/agents

# Set permissions
chmod -R 755 "$REPO_DIR"

echo ""
echo "✅ Agent workspace setup complete!"
echo ""
echo "📁 Workspace location: $REPO_DIR"
echo ""
echo "📝 Next steps:"
echo "1. Update the agent configuration to use this workspace"
echo "2. Restart agents with: ./start-devteam.sh"
echo "3. Agents can now:"
echo "   - Create feature branches"
echo "   - Make code changes"
echo "   - Commit and push changes"
echo "   - Create pull requests"
echo ""
echo "🤖 To test agent file operations:"
echo "   Send a message like: @frontend please update the menu colors in $REPO_DIR"