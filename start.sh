#!/bin/bash
# Start both backend and frontend in parallel

echo "🎬 Starting Claude × DaVinci Resolve..."
echo ""

# Check for .env
if [ ! -f "backend/.env" ]; then
  echo "⚠️  backend/.env not found. Copying from example..."
  cp backend/.env.example backend/.env
  echo "📝 Please edit backend/.env and add your ANTHROPIC_API_KEY, then run again."
  exit 1
fi

# Check for Resolve scripting
echo "📡 Starting Python backend on :8765..."
cd backend
if [ ! -d "venv" ]; then
  echo "🔧 Creating Python venv..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi

python main.py &
BACKEND_PID=$!
cd ..

echo "⚡ Starting React frontend on :5173..."
cd frontend
if [ ! -d "node_modules" ]; then
  echo "📦 Installing npm packages..."
  npm install -q
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8765"
echo ""
echo "Press Ctrl+C to stop both."

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
