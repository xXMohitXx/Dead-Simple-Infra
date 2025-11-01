import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ArrowLeft, Play, Trash2, Key, Activity, Terminal as TerminalIcon } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AppDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState(null);
  const [deployments, setDeployments] = useState([]);
  const [secrets, setSecrets] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [logs, setLogs] = useState([]);
  const [newSecret, setNewSecret] = useState({ key: "", value: "" });
  const [isSecretDialogOpen, setIsSecretDialogOpen] = useState(false);
  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    fetchAppDetails();
    fetchDeployments();
    fetchSecrets();
    fetchMetrics();

    // Set up SSE for logs
    connectToLogs();

    const interval = setInterval(() => {
      fetchAppDetails();
      fetchMetrics();
    }, 3000);

    return () => {
      clearInterval(interval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [id]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const connectToLogs = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(`${API}/v1/apps/${id}/logs/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const logData = JSON.parse(event.data);
        setLogs((prev) => [...prev, logData]);
      } catch (error) {
        console.error("Failed to parse log data:", error);
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE connection error:", error);
      eventSource.close();
      // Reconnect after 5 seconds
      setTimeout(connectToLogs, 5000);
    };
  };

  const fetchAppDetails = async () => {
    try {
      const response = await axios.get(`${API}/v1/apps/${id}`);
      setApp(response.data);
    } catch (error) {
      console.error("Failed to fetch app details:", error);
      toast.error("Failed to load app details");
    }
  };

  const fetchDeployments = async () => {
    try {
      const response = await axios.get(`${API}/v1/deployments/${id}`);
      setDeployments(response.data);
    } catch (error) {
      console.error("Failed to fetch deployments:", error);
    }
  };

  const fetchSecrets = async () => {
    try {
      const response = await axios.get(`${API}/v1/apps/${id}/secrets`);
      setSecrets(response.data);
    } catch (error) {
      console.error("Failed to fetch secrets:", error);
    }
  };

  const fetchMetrics = async () => {
    try {
      const response = await axios.get(`${API}/v1/apps/${id}/metrics?limit=20`);
      setMetrics(response.data);
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    }
  };

  const handleDeploy = async () => {
    try {
      await axios.post(`${API}/v1/apps/${id}/deploy`);
      toast.success("Deployment started");
      setLogs([]);
      fetchAppDetails();
      fetchDeployments();
    } catch (error) {
      toast.error("Failed to start deployment");
      console.error(error);
    }
  };

  const handleAddSecret = async () => {
    if (!newSecret.key || !newSecret.value) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      await axios.post(`${API}/v1/apps/${id}/secrets`, newSecret);
      toast.success("Secret added successfully");
      setNewSecret({ key: "", value: "" });
      setIsSecretDialogOpen(false);
      fetchSecrets();
    } catch (error) {
      toast.error("Failed to add secret");
      console.error(error);
    }
  };

  const handleDeleteSecret = async (secretId, secretKey) => {
    if (!window.confirm(`Delete secret "${secretKey}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API}/v1/apps/${id}/secrets/${secretId}`);
      toast.success("Secret deleted");
      fetchSecrets();
    } catch (error) {
      toast.error("Failed to delete secret");
      console.error(error);
    }
  };

  const handleDeleteApp = async () => {
    if (!window.confirm(`Are you sure you want to delete "${app?.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await axios.delete(`${API}/v1/apps/${id}`);
      toast.success("App deleted");
      navigate("/");
    } catch (error) {
      toast.error("Failed to delete app");
      console.error(error);
    }
  };

  if (!app) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%)" }}>
        <Activity className="w-8 h-8 animate-spin" style={{ color: "#58a6ff" }} />
      </div>
    );
  }

  const latestMetric = metrics.length > 0 ? metrics[0] : null;

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%)" }}>
      {/* Header */}
      <div className="border-b" style={{ borderColor: "#30363d", background: "rgba(13, 17, 23, 0.8)", backdropFilter: "blur(12px)" }}>
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                data-testid="back-button"
                variant="ghost"
                size="sm"
                onClick={() => navigate("/")}
                style={{ color: "#8b949e" }}
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold" style={{ color: "#e4e7eb" }}>{app.name}</h1>
                <p className="text-sm" style={{ color: "#8b949e" }}>{app.repo_url}</p>
              </div>
              <span className={`status-badge ${app.status}`}>
                <span className="status-dot"></span>
                {app.status}
              </span>
            </div>

            <div className="flex gap-3">
              <Button
                data-testid="deploy-action-button"
                onClick={handleDeploy}
                disabled={app.status === "building"}
                className="gap-2"
                style={{ background: "#238636", color: "white", border: "none" }}
              >
                <Play className="w-4 h-4" />
                Deploy
              </Button>
              <Button
                data-testid="delete-app-button"
                onClick={handleDeleteApp}
                variant="destructive"
                className="gap-2"
                style={{ background: "#da3633", color: "white", border: "none" }}
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Metrics */}
        {latestMetric && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="metric-card" data-testid="metric-cpu">
              <div className="metric-value">{latestMetric.cpu_percent.toFixed(1)}%</div>
              <div className="metric-label">CPU Usage</div>
            </div>
            <div className="metric-card" data-testid="metric-memory">
              <div className="metric-value">{latestMetric.memory_mb.toFixed(0)} MB</div>
              <div className="metric-label">Memory</div>
            </div>
            <div className="metric-card" data-testid="metric-uptime">
              <div className="metric-value">{latestMetric.uptime_seconds}s</div>
              <div className="metric-label">Uptime</div>
            </div>
            <div className="metric-card" data-testid="metric-requests">
              <div className="metric-value">{latestMetric.request_count}</div>
              <div className="metric-label">Requests</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="logs" className="space-y-4">
          <TabsList style={{ background: "#0d1117", border: "1px solid #30363d" }}>
            <TabsTrigger data-testid="logs-tab" value="logs" style={{ color: "#8b949e" }}>Logs</TabsTrigger>
            <TabsTrigger data-testid="deployments-tab" value="deployments" style={{ color: "#8b949e" }}>Deployments</TabsTrigger>
            <TabsTrigger data-testid="secrets-tab" value="secrets" style={{ color: "#8b949e" }}>Secrets</TabsTrigger>
          </TabsList>

          {/* Logs Tab */}
          <TabsContent value="logs" data-testid="logs-content">
            <div className="terminal" style={{ height: "500px", overflowY: "auto" }}>
              <div className="terminal-header">
                <div className="terminal-dot red"></div>
                <div className="terminal-dot yellow"></div>
                <div className="terminal-dot green"></div>
                <span style={{ fontSize: "13px", color: "#8b949e" }}>Application Logs</span>
              </div>
              <div className="terminal-output">
                {logs.length === 0 ? (
                  <div style={{ color: "#6e7681", textAlign: "center", padding: "40px" }}>
                    <TerminalIcon className="w-12 h-12 mx-auto mb-2" style={{ color: "#30363d" }} />
                    <p>No logs yet. Deploy your app to see logs.</p>
                  </div>
                ) : (
                  logs.map((log, idx) => (
                    <div key={idx} data-testid={`log-entry-${idx}`}>
                      <span className="terminal-prompt">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{" "}
                      <span>{log.log}</span>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          </TabsContent>

          {/* Deployments Tab */}
          <TabsContent value="deployments" data-testid="deployments-content">
            <div className="space-y-4">
              {deployments.length === 0 ? (
                <div className="text-center py-16" style={{ color: "#6e7681" }}>
                  <p>No deployments yet</p>
                </div>
              ) : (
                deployments.map((deployment) => (
                  <div key={deployment.id} data-testid={`deployment-${deployment.id}`} className="card">
                    <div className="flex items-center justify-between mb-2">
                      <span style={{ color: "#8b949e", fontSize: "13px", fontFamily: "'Space Mono', monospace" }}>
                        {deployment.id}
                      </span>
                      <span className={`status-badge ${deployment.status}`}>
                        <span className="status-dot"></span>
                        {deployment.status}
                      </span>
                    </div>
                    <div style={{ color: "#6e7681", fontSize: "13px" }}>
                      Started: {new Date(deployment.started_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>

          {/* Secrets Tab */}
          <TabsContent value="secrets" data-testid="secrets-content">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <p style={{ color: "#8b949e" }}>Manage environment variables and secrets</p>
                <Dialog open={isSecretDialogOpen} onOpenChange={setIsSecretDialogOpen}>
                  <DialogTrigger asChild>
                    <Button data-testid="add-secret-button" className="gap-2" style={{ background: "#238636", color: "white", border: "none" }}>
                      <Key className="w-4 h-4" />
                      Add Secret
                    </Button>
                  </DialogTrigger>
                  <DialogContent data-testid="add-secret-dialog" style={{ background: "#0d1117", border: "1px solid #30363d", color: "#e4e7eb" }}>
                    <DialogHeader>
                      <DialogTitle style={{ color: "#e4e7eb" }}>Add Secret</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 mt-4">
                      <div>
                        <Label style={{ color: "#8b949e" }}>Key</Label>
                        <Input
                          data-testid="secret-key-input"
                          placeholder="DATABASE_URL"
                          value={newSecret.key}
                          onChange={(e) => setNewSecret({ ...newSecret, key: e.target.value })}
                          style={{ background: "#161b22", border: "1px solid #30363d", color: "#e4e7eb" }}
                        />
                      </div>
                      <div>
                        <Label style={{ color: "#8b949e" }}>Value</Label>
                        <Input
                          data-testid="secret-value-input"
                          type="password"
                          placeholder="postgres://..."
                          value={newSecret.value}
                          onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
                          style={{ background: "#161b22", border: "1px solid #30363d", color: "#e4e7eb" }}
                        />
                      </div>
                      <Button data-testid="save-secret-button" onClick={handleAddSecret} className="w-full" style={{ background: "#238636", color: "white", border: "none" }}>
                        Save Secret
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>

              {secrets.length === 0 ? (
                <div className="text-center py-16" style={{ color: "#6e7681" }}>
                  <Key className="w-12 h-12 mx-auto mb-2" style={{ color: "#30363d" }} />
                  <p>No secrets configured</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {secrets.map((secret) => (
                    <div key={secret.id} data-testid={`secret-${secret.id}`} className="card flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Key className="w-4 h-4" style={{ color: "#58a6ff" }} />
                        <span style={{ color: "#e4e7eb", fontFamily: "'Space Mono', monospace" }}>{secret.key}</span>
                      </div>
                      <Button
                        data-testid={`delete-secret-${secret.id}`}
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteSecret(secret.id, secret.key)}
                        style={{ color: "#f85149" }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AppDetails;
