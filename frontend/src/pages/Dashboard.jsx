import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Server, GitBranch, Activity, Terminal } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const navigate = useNavigate();
  const [apps, setApps] = useState([]);
  const [agents, setAgents] = useState([]);
  const [isNewAppOpen, setIsNewAppOpen] = useState(false);
  const [newApp, setNewApp] = useState({ name: "", repo_url: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApps();
    fetchAgents();
    const interval = setInterval(() => {
      fetchApps();
      fetchAgents();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchApps = async () => {
    try {
      const response = await axios.get(`${API}/v1/apps`);
      setApps(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Failed to fetch apps:", error);
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await axios.get(`${API}/v1/agents`);
      setAgents(response.data);
    } catch (error) {
      console.error("Failed to fetch agents:", error);
    }
  };

  const handleCreateApp = async () => {
    if (!newApp.name || !newApp.repo_url) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      const response = await axios.post(`${API}/v1/apps`, {
        name: newApp.name,
        repo_url: newApp.repo_url,
        repo_type: "git"
      });
      toast.success(`App "${newApp.name}" created successfully`);
      setNewApp({ name: "", repo_url: "" });
      setIsNewAppOpen(false);
      fetchApps();
    } catch (error) {
      toast.error("Failed to create app");
      console.error(error);
    }
  };

  const handleDeploy = async (appId, appName) => {
    try {
      await axios.post(`${API}/v1/apps/${appId}/deploy`);
      toast.success(`Deployment started for "${appName}"`);
      fetchApps();
    } catch (error) {
      toast.error("Failed to start deployment");
      console.error(error);
    }
  };

  const handleDeleteApp = async (appId, appName) => {
    if (!window.confirm(`Are you sure you want to delete "${appName}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API}/v1/apps/${appId}`);
      toast.success(`App "${appName}" deleted`);
      fetchApps();
    } catch (error) {
      toast.error("Failed to delete app");
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%)" }}>
      {/* Header */}
      <div className="border-b" style={{ borderColor: "#30363d", background: "rgba(13, 17, 23, 0.8)", backdropFilter: "blur(12px)" }}>
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ background: "linear-gradient(135deg, #58a6ff, #8957e5)" }}>
                <Terminal className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold" style={{ color: "#e4e7eb", fontFamily: "'Space Mono', monospace" }}>
                  Dead Simple Infrastructure
                </h1>
                <p className="text-sm" style={{ color: "#8b949e" }}>Local-first deployment console</p>
              </div>
            </div>

            <Dialog open={isNewAppOpen} onOpenChange={setIsNewAppOpen}>
              <DialogTrigger asChild>
                <Button data-testid="new-app-button" className="gap-2" style={{ background: "linear-gradient(135deg, #58a6ff, #8957e5)", color: "white", border: "none" }}>
                  <Plus className="w-4 h-4" />
                  New App
                </Button>
              </DialogTrigger>
              <DialogContent data-testid="new-app-dialog" style={{ background: "#0d1117", border: "1px solid #30363d", color: "#e4e7eb" }}>
                <DialogHeader>
                  <DialogTitle style={{ color: "#e4e7eb" }}>Create New App</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div>
                    <Label style={{ color: "#8b949e" }}>App Name</Label>
                    <Input
                      data-testid="app-name-input"
                      placeholder="my-awesome-app"
                      value={newApp.name}
                      onChange={(e) => setNewApp({ ...newApp, name: e.target.value })}
                      style={{ background: "#161b22", border: "1px solid #30363d", color: "#e4e7eb" }}
                    />
                  </div>
                  <div>
                    <Label style={{ color: "#8b949e" }}>Git Repository URL</Label>
                    <Input
                      data-testid="repo-url-input"
                      placeholder="https://github.com/user/repo.git"
                      value={newApp.repo_url}
                      onChange={(e) => setNewApp({ ...newApp, repo_url: e.target.value })}
                      style={{ background: "#161b22", border: "1px solid #30363d", color: "#e4e7eb" }}
                    />
                  </div>
                  <Button data-testid="create-app-submit" onClick={handleCreateApp} className="w-full" style={{ background: "linear-gradient(135deg, #58a6ff, #8957e5)", color: "white", border: "none" }}>
                    Create App
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Agent Status */}
        <div className="mb-8 p-4 rounded-lg" style={{ background: "#0d1117", border: "1px solid #30363d" }}>
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5" style={{ color: "#58a6ff" }} />
            <span style={{ color: "#e4e7eb", fontWeight: 600 }}>Agents:</span>
            {agents.length === 0 ? (
              <span data-testid="agent-status-offline" className="status-badge stopped">
                <span className="status-dot"></span>
                No agents connected
              </span>
            ) : (
              agents.map((agent) => (
                <span data-testid={`agent-status-${agent.id}`} key={agent.id} className="status-badge running">
                  <span className="status-dot"></span>
                  {agent.name}
                </span>
              ))
            )}
          </div>
        </div>

        {/* Apps Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Activity className="w-8 h-8 animate-spin mx-auto mb-2" style={{ color: "#58a6ff" }} />
              <p style={{ color: "#8b949e" }}>Loading...</p>
            </div>
          </div>
        ) : apps.length === 0 ? (
          <div className="text-center py-16">
            <Terminal className="w-16 h-16 mx-auto mb-4" style={{ color: "#30363d" }} />
            <h3 className="text-xl font-semibold mb-2" style={{ color: "#8b949e" }}>No apps yet</h3>
            <p className="mb-6" style={{ color: "#6e7681" }}>Create your first app to get started</p>
            <Button data-testid="empty-state-create-button" onClick={() => setIsNewAppOpen(true)} className="gap-2" style={{ background: "linear-gradient(135deg, #58a6ff, #8957e5)", color: "white", border: "none" }}>
              <Plus className="w-4 h-4" />
              Create App
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {apps.map((app) => (
              <div
                key={app.id}
                data-testid={`app-card-${app.id}`}
                className="card cursor-pointer"
                onClick={() => navigate(`/apps/${app.id}`)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-2" style={{ color: "#e4e7eb" }}>{app.name}</h3>
                    <div className="flex items-center gap-2 text-sm" style={{ color: "#8b949e" }}>
                      <GitBranch className="w-4 h-4" />
                      <span className="truncate">{app.repo_url}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className={`status-badge ${app.status}`}>
                    <span className="status-dot"></span>
                    {app.status}
                  </span>

                  {app.status === "idle" && (
                    <Button
                      data-testid={`deploy-button-${app.id}`}
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeploy(app.id, app.name);
                      }}
                      style={{ background: "#238636", color: "white", border: "none" }}
                    >
                      Deploy
                    </Button>
                  )}
                </div>

                {app.url && (
                  <div className="mt-4 pt-4" style={{ borderTop: "1px solid #21262d" }}>
                    <a
                      data-testid={`app-url-${app.id}`}
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-sm"
                      style={{ color: "#58a6ff", textDecoration: "none" }}
                    >
                      {app.url}
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
