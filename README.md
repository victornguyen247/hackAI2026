# 🚀 Learning Route Advisor

An elegant, AI-powered platform for generating and tracking personalized learning journeys. Build your own roadmap or discover community paths, all while interacting with an intelligent AI Advisor to guide your growth.

## ✨ Features

- **AI-Generated Roadmaps**: Instantly generate structured learning paths for any goal using Google Gemini.
- **Interactive Mind Map**: Visualize your journey using a dynamic, color-coded ReactFlow canvas.
- **AI Advisor Bot**: A real-time chat agent to explain concepts and suggest resources.
- **Progress Tracking**: Mark nodes as completed, track resource usage, and unlock new levels.
- **Community Discovery**: Search for and clone public roadmaps from other explorers.
- **Elegant Paper Aesthetic**: A premium UI designed with a beige-white "paper note" theme.

## 🛠 Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
- **AI Engine**: [Google Gemini 2.5 Flash](https://ai.google.dev/)
- **API**: RESTful architecture with automatic Swagger documentation.

### Frontend
- **Framework**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
- **Visuals**: [ReactFlow](https://reactflow.dev/) for interactive mapping.
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) with a custom design system.
- **Icons**: [Lucide React](https://lucide.dev/)

---

## 🏃 Getting Started

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- Google Gemini API Key

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_api_key_here
```
Run the server:
```bash
python3 -m uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📖 How to Use

### 1. Create Your First Roadmap
When you log in for the first time, you'll be greeted by the Onboarding screen. Simply describe what you want to learn (e.g., "I want to become a Full-Stack Web Developer" or "Learn the basics of Machine Learning"). Our AI will generate a personalized roadmap customized to your goals.

> *(Placeholder for Onboarding Screen Image)*
> `![Onboarding Screen](path/to/your/image.png)`

### 2. Navigate the Interactive Mind Map
Your generated learning path is displayed as a beautiful, interactive node graph. 
- **Zoom & Pan**: Use your mouse or trackpad to explore the canvas.
- **Node Status**: Nodes represent topics. Gray nodes are locked until you complete prerequisites. Blue nodes are ready to learn. Green nodes are completed.

> *(Placeholder for Interactive Map Image)*
> `![Interactive Map View](path/to/your/image.png)`

### 3. Expand Topics
If a topic is broad, click **"Expand"** in the sidebar. The AI will break it down into smaller, more manageable sub-topics and dynamically add them to your map, allowing you to dive as deep as you need into specific concepts.

> *(Placeholder for Expanding Nodes Image)*
> `![Expanding Nodes Highlight](path/to/your/image.png)`

### 4. Discover Learning Resources
Clicking on any unlocked node opens the **Resource Sidebar**. The AI automatically curates the best web resources (YouTube videos, official documentation, articles) specifically tailored to that node's topic. You can also add your own custom resources.

> *(Placeholder for Resource Sidebar Image)*
> `![Resource Sidebar with Links](path/to/your/image.png)`

### 5. Chat with the AI Advisor
Stuck on a concept? Need curriculum advice? Click the **Chat window** in the bottom right corner to talk directly to your personalized Learning Advisor AI. It has context on your current goal and can guide you through difficult topics.

> *(Placeholder for AI Advisor Chat Image)*
> `![AI Chat Window](path/to/your/image.png)`

### 6. Explore Community Maps
Looking for inspiration? Use the top navigation bar to search for other users by username. You can view their public roadmaps and hit the **Clone** button to copy their learning journey to your own dashboard.

> *(Placeholder for Community Maps/Search Image)*
> `![Searching and Cloning Maps](path/to/your/image.png)`

---

## 🔍 Debugging
For detailed troubleshooting, logs, and common issues, please refer to the [DEBUGGING.md](DEBUGGING.md) guide.
