import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAdminStore from "../../store/adminStore";
import Button from "../common/Button";

export default function AdminLogin() {
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");
    const navigate = useNavigate();
    
    const { login, isAuthenticated, isLoading, error, checkAuth } = useAdminStore();

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        if (isAuthenticated) {
            navigate("/admin");
        }
    }, [isAuthenticated, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!usernameInput.trim() || !passwordInput.trim()) return;
        await login(usernameInput, passwordInput);
    };

    return (
        <section className="portal" style={{ maxWidth: "420px" }}>
            <div className="portal-view">
                <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔒</div>
                <h2 style={{ marginBottom: "0.5rem" }}>Admin Portal</h2>
                <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1.5rem", textAlign: "center" }}>
                    Sign in to manage PisoWiFi Hotspot
                </p>

                {error && (
                    <div style={{
                        color: "#ff5a5a",
                        background: "rgba(255, 90, 90, 0.08)",
                        border: "1px solid rgba(255, 90, 90, 0.15)",
                        borderRadius: "12px",
                        padding: "12px",
                        width: "100%",
                        fontSize: "0.85rem",
                        marginBottom: "1.2rem",
                        textAlign: "center"
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ width: "100%", display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", alignItems: "flex-start" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500" }}>Username</label>
                        <input
                            type="text"
                            placeholder="Enter username"
                            value={usernameInput}
                            onChange={(e) => setUsernameInput(e.target.value)}
                            style={{
                                width: "100%",
                                padding: "12px 16px",
                                background: "rgba(255, 255, 255, 0.03)",
                                border: "1px solid var(--border)",
                                borderRadius: "10px",
                                color: "#fff",
                                fontSize: "0.95rem",
                                outline: "none",
                                transition: "all 0.2s ease"
                            }}
                            onFocus={(e) => e.target.style.borderColor = "var(--primary)"}
                            onBlur={(e) => e.target.style.borderColor = "var(--border)"}
                            required
                        />
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", alignItems: "flex-start" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500" }}>Password</label>
                        <input
                            type="password"
                            placeholder="Enter password"
                            value={passwordInput}
                            onChange={(e) => setPasswordInput(e.target.value)}
                            style={{
                                width: "100%",
                                padding: "12px 16px",
                                background: "rgba(255, 255, 255, 0.03)",
                                border: "1px solid var(--border)",
                                borderRadius: "10px",
                                color: "#fff",
                                fontSize: "0.95rem",
                                outline: "none",
                                transition: "all 0.2s ease"
                            }}
                            onFocus={(e) => e.target.style.borderColor = "var(--primary)"}
                            onBlur={(e) => e.target.style.borderColor = "var(--border)"}
                            required
                        />
                    </div>

                    <div style={{ marginTop: "1rem" }}>
                        <Button
                            type="submit"
                            disabled={isLoading}
                            variant="primary"
                        >
                            {isLoading ? "Signing in..." : "Sign In"}
                        </Button>
                    </div>
                </form>
            </div>
        </section>
    );
}
