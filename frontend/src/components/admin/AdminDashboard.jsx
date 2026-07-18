import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useAdminStore from "../../store/adminStore";
import adminApi from "../../api/adminClient";
import "../../styles/admin.css";

export default function AdminDashboard() {
    const { isAuthenticated, isLoading, logout, username, checkAuth } = useAdminStore();
    const [data, setData] = useState(null);
    const [fetchError, setFetchError] = useState(null);
    const navigate = useNavigate();

    // Check authentication on load
    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    // Aggregate fetch endpoint (single call every 5 seconds)
    const fetchDashboard = useCallback(async () => {
        try {
            const res = await adminApi.get("/dashboard");
            if (res.data?.success) {
                setData(res.data.data);
                setFetchError(null);
            } else {
                setFetchError(res.data?.message || "Failed to compile dashboard");
            }
        } catch (err) {
            console.error("Dashboard fetch failed:", err);
            setFetchError("Failed to connect to backend API");
        }
    }, []);

    // Set up polling interval with visibility detection (pauses when backgrounded to save resources)
    useEffect(() => {
        if (!isAuthenticated) return;

        let intervalId = null;

        const startPolling = () => {
            if (intervalId) return;
            fetchDashboard();
            intervalId = setInterval(fetchDashboard, 15000);
        };

        const stopPolling = () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        };

        const handleVisibilityChange = () => {
            if (document.visibilityState === "visible") {
                startPolling();
            } else {
                stopPolling();
            }
        };

        // Initialize polling based on visibility
        if (document.visibilityState === "visible") {
            startPolling();
        }

        document.addEventListener("visibilitychange", handleVisibilityChange);

        return () => {
            stopPolling();
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
    }, [isAuthenticated, fetchDashboard]);

    // Redirect if unauthenticated
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            navigate("/admin/login");
        }
    }, [isAuthenticated, isLoading, navigate]);

    if (isLoading) {
        return (
            <section className="portal" style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "300px" }}>
                <div style={{ color: "var(--muted)", fontSize: "0.95rem" }}>Loading admin...</div>
            </section>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    const handleLogout = async () => {
        await logout();
        navigate("/admin/login");
    };

    const formatUptime = (seconds) => {
        if (!seconds) return "0s";
        const d = Math.floor(seconds / (3600 * 24));
        const h = Math.floor((seconds % (3600 * 24)) / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        const parts = [];
        if (d > 0) parts.push(`${d}d`);
        if (h > 0) parts.push(`${h}h`);
        if (m > 0) parts.push(`${m}m`);
        if (parts.length === 0 || s > 0) parts.push(`${s}s`);
        return parts.join(" ");
    };

    const formatSeconds = (sec) => {
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    };

    const formatBytes = (bytes) => {
        if (!bytes) return "0 GB";
        const gb = bytes / (1024 * 1024 * 1024);
        return `${gb.toFixed(2)} GB`;
    };

    const formatDateTime = (isoString) => {
        if (!isoString) return "N/A";
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
            return "N/A";
        }
    };

    const formatPurchased = (seconds) => {
        if (!seconds) return "0m";
        const m = Math.floor(seconds / 60);
        if (m >= 60) {
            const h = m / 60;
            return `${h.toFixed(1)}h`;
        }
        return `${m}m`;
    };

    return (
        <section className="admin-layout">
            {/* Main Area */}
            <div className="admin-content">
                <header className="admin-header">
                    <div>
                        <h2 style={{ fontSize: "1.6rem", fontWeight: "700", color: "#fff", letterSpacing: "-0.5px" }}>Dashboard Analytics</h2>
                        <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "4px" }}>Real-time gateway monitoring statistics</p>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                        <div className="live-indicator">
                            <span className="live-dot"></span>
                            <span>Live Syncing</span>
                        </div>
                        <div style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            borderLeft: "1px solid var(--border)",
                            paddingLeft: "20px"
                        }}>
                            <span style={{ fontSize: "0.9rem", color: "#fff", fontWeight: "500" }}>👤 {username}</span>
                            <button onClick={handleLogout} className="signout-btn">
                                Sign Out
                            </button>
                        </div>
                    </div>
                </header>


                {fetchError && (
                    <div style={{
                        color: "#ff5a5a",
                        background: "rgba(255, 90, 90, 0.08)",
                        border: "1px solid rgba(255, 90, 90, 0.15)",
                        borderRadius: "12px",
                        padding: "12px",
                        fontSize: "0.85rem",
                        marginBottom: "20px",
                        textAlign: "center"
                    }}>
                        ⚠️ {fetchError} (Polling continues...)
                    </div>
                )}

                {data && data.system_health.admin_mode?.default_credentials_detected && (
                    <div style={{
                        color: "#ff5a5a",
                        background: "rgba(255, 90, 90, 0.04)",
                        border: "1px solid rgba(255, 90, 90, 0.3)",
                        borderRadius: "12px",
                        padding: "16px",
                        fontSize: "0.9rem",
                        marginBottom: "20px",
                        textAlign: "left",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px"
                    }}>
                        <strong style={{ display: "flex", alignItems: "center", gap: "8px", color: "#ff5a5a" }}>
                            ⚠️ CRITICAL SECURITY WARNING: Default Credentials Detected
                        </strong>
                        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                            Your system is currently using the default administrator credentials (<strong>admin / admin123</strong>). This is a severe security vulnerability. Please define secure, unique credentials in the <code>.env</code> file immediately to protect the administration gateway.
                        </span>
                    </div>
                )}

                {data && data.system_health.admin_mode?.plaintext_password_mode && !data.system_health.admin_mode?.default_credentials_detected && (
                    <div style={{
                        color: "#f59e0b",
                        background: "rgba(245, 158, 11, 0.04)",
                        border: "1px solid rgba(245, 158, 11, 0.3)",
                        borderRadius: "12px",
                        padding: "16px",
                        fontSize: "0.9rem",
                        marginBottom: "20px",
                        textAlign: "left",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px"
                    }}>
                        <strong style={{ display: "flex", alignItems: "center", gap: "8px", color: "#f59e0b" }}>
                            ⚠️ Security Recommendation: Plaintext Password Mode Active
                        </strong>
                        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                            Your administration credentials are currently stored in plaintext. We recommend migrating to <code>ADMIN_PASSWORD_HASH</code> using bcrypt. Generate a bcrypt hash and configure it in your <code>.env</code> to disable plaintext mode.
                        </span>
                    </div>
                )}

                {!data ? (
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", flex: 1 }}>
                        <div style={{ color: "var(--muted)" }}>Collecting server status...</div>
                    </div>
                ) : (
                    <>
                        {/* Sales Grid */}
                        <div className="sales-grid">
                            <div className="sales-card">
                                <span className="sales-title">Today's Revenue</span>
                                <span className="sales-amount">₱{data.sales.today}</span>
                            </div>
                            <div className="sales-card">
                                <span className="sales-title">Weekly Revenue</span>
                                <span className="sales-amount">₱{data.sales.week}</span>
                            </div>
                            <div className="sales-card">
                                <span className="sales-title">Monthly Revenue</span>
                                <span className="sales-amount">₱{data.sales.month}</span>
                            </div>
                        </div>

                        {/* Mid Section: Server Info and Health */}
                        <div className="dashboard-sections">
                            {/* Server Info Card */}
                            <div className="section-card">
                                <h3 className="section-title">Server Information</h3>
                                <div className="info-list">
                                    <div className="info-item">
                                        <span className="info-label">Hostname</span>
                                        <span className="info-value">{data.system_health.hostname}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">Uptime</span>
                                        <span className="info-value">{formatUptime(data.system_health.system_uptime)}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">LAN Interface</span>
                                        <span className="info-value">{data.system_health.lan_interface}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">WAN Interface</span>
                                        <span className="info-value">{data.system_health.wan_interface}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">Kernel</span>
                                        <span className="info-value" style={{ fontSize: "0.8rem" }}>{data.system_health.kernel_version}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">Python Version</span>
                                        <span className="info-value">{data.system_health.python_version}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">Timezone</span>
                                        <span className="info-value">{data.system_health.timezone}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="info-label">Active / Auth Clients</span>
                                        <span className="info-value">{data.system_health.active_sessions_count} Active / {data.system_health.authenticated_clients_count} Auth</span>
                                    </div>
                                </div>
                            </div>

                            {/* System Health Card */}
                            <div className="section-card">
                                <h3 className="section-title">System Health & Diagnostics</h3>
                                <div className="health-grid">
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Backend</span>
                                            <span className={`health-status ${data.system_health.backend_service_active ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.backend_status}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Database</span>
                                            <span className={`health-status ${data.system_health.database_connected ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.database_details ? "Connected" : "Offline"}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Coin Serial</span>
                                            <span className={`health-status ${data.system_health.coin_listener_connected ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail" style={{ textTransform: "lowercase", fontSize: "0.7rem" }}>{data.system_health.coin_listener_port}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Scheduler</span>
                                            <span className={`health-status ${data.system_health.scheduler_active ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.scheduler_active ? "Active" : "Inactive"}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Firewall</span>
                                            <span className={`health-status ${data.system_health.firewall_active ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">nftables active</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Internet</span>
                                            <span className={`health-status ${data.system_health.internet_connected ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.internet_connected ? "Connected" : "Disconnected"}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">DNS Status</span>
                                            <span className={`health-status ${data.system_health.dns_ok ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.dns_ok ? "DNS Online" : "Unresolved"}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">Nginx Web</span>
                                            <span className={`health-status ${data.system_health.nginx_active ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.nginx_active ? "Active" : "Offline"}</span>
                                    </div>
                                    <div className="health-item">
                                        <div className="health-header">
                                            <span className="health-label">MariaDB</span>
                                            <span className={`health-status ${data.system_health.mariadb_active ? "status-online" : "status-offline"}`}></span>
                                        </div>
                                        <span className="health-detail">{data.system_health.mariadb_active ? "Active" : "Offline"}</span>
                                    </div>
                                </div>

                                {/* Resource bars */}
                                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
                                    <div>
                                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                                            <span style={{ color: "var(--muted)" }}>CPU Usage</span>
                                            <span style={{ color: "#fff", fontWeight: "600" }}>{data.system_health.cpu_usage_percent}%</span>
                                        </div>
                                        <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                                            <div style={{ width: `${data.system_health.cpu_usage_percent}%`, height: "100%", background: "var(--primary)", borderRadius: "3px" }}></div>
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                                            <span style={{ color: "var(--muted)" }}>RAM Usage ({formatBytes(data.system_health.ram_used)} / {formatBytes(data.system_health.ram_total)})</span>
                                            <span style={{ color: "#fff", fontWeight: "600" }}>{data.system_health.ram_usage_percent}%</span>
                                        </div>
                                        <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                                            <div style={{ width: `${data.system_health.ram_usage_percent}%`, height: "100%", background: "var(--secondary)", borderRadius: "3px" }}></div>
                                        </div>
                                    </div>
                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                                        <div>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                                                <span style={{ color: "var(--muted)" }}>Disk ({formatBytes(data.system_health.disk_used)})</span>
                                                <span style={{ color: "#fff" }}>{data.system_health.disk_usage_percent}%</span>
                                            </div>
                                            <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                                                <div style={{ width: `${data.system_health.disk_usage_percent}%`, height: "100%", background: "#a6b2d3", borderRadius: "3px" }}></div>
                                            </div>
                                        </div>
                                        <div>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                                                <span style={{ color: "var(--muted)" }}>CPU Temp</span>
                                                <span style={{ color: data.system_health.cpu_temperature > 65 ? "#ef4444" : "#fff" }}>
                                                    {data.system_health.cpu_temperature ? `${data.system_health.cpu_temperature}°C` : "N/A"}
                                                </span>
                                            </div>
                                            <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                                                <div style={{ 
                                                    width: data.system_health.cpu_temperature ? `${Math.min(100, (data.system_health.cpu_temperature / 90) * 100)}%` : "0%", 
                                                    height: "100%", 
                                                    background: data.system_health.cpu_temperature > 65 ? "#ef4444" : "var(--primary)", 
                                                    borderRadius: "3px" 
                                                }}></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Active Users Table */}
                        <div className="users-table-container">
                            <h3 className="section-title" style={{ borderBottom: "none", paddingBottom: 0, marginBottom: "16px" }}>Active Clients ({data.active_users.length})</h3>
                            {data.active_users.length === 0 ? (
                                <div style={{ padding: "20px", textAlign: "center", color: "var(--muted)" }}>
                                    No active user sessions currently.
                                </div>
                            ) : (
                                <table className="users-table">
                                    <thead>
                                        <tr>
                                            <th>IP Address</th>
                                            <th>MAC Address</th>
                                            <th>Remaining Time</th>
                                            <th>Purchased Time</th>
                                            <th>Status</th>
                                            <th>Connected Since</th>
                                            <th>Last Activity</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.active_users.map((user) => (
                                            <tr key={user.mac}>
                                                <td style={{ fontFamily: "monospace" }}>{user.ip}</td>
                                                <td style={{ fontFamily: "monospace" }}>{user.mac}</td>
                                                <td style={{ color: "var(--primary)", fontWeight: "600", fontFamily: "monospace" }}>{formatSeconds(user.remaining_time)}</td>
                                                <td>{formatPurchased(user.purchased_time)}</td>
                                                <td>
                                                    <span className={`admin-status-badge ${
                                                        (user.status || "").toUpperCase() === "ACTIVE" ? "badge-active" :
                                                        (user.status || "").toUpperCase() === "PAUSED" ? "badge-paused" :
                                                        (user.status || "").toUpperCase() === "EXPIRED" ? "badge-expired" :
                                                        "badge-offline"
                                                    }`}>
                                                        {(user.status || "").toUpperCase()}
                                                    </span>
                                                </td>
                                                <td>{formatDateTime(user.connected_time)}</td>
                                                <td>{formatDateTime(user.last_activity)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </>
                )}
            </div>
        </section>
    );
}
