import { useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import useAdminStore from "../../store/adminStore";

export default function AdminSettings({ currentUsername }) {
    const navigate = useNavigate();
    const logout = useAdminStore((state) => state.logout);

    const [activeTab, setActiveTab] = useState("password"); // "username" or "password"

    // Username state
    const [userForm, setUserForm] = useState({ currentPassword: "", newUsername: "" });
    const [userLoading, setUserLoading] = useState(false);
    const [userError, setUserError] = useState("");
    const [userSuccess, setUserSuccess] = useState("");

    // Password state
    const [passForm, setPassForm] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });
    const [passLoading, setPassLoading] = useState(false);
    const [passError, setPassError] = useState("");
    const [passSuccess, setPassSuccess] = useState("");

    const handleUsernameSubmit = async (e) => {
        e.preventDefault();
        setUserError("");
        setUserSuccess("");

        if (!userForm.currentPassword) {
            setUserError("Current password is required.");
            return;
        }
        if (!userForm.newUsername || userForm.newUsername.trim().length < 3) {
            setUserError("New username must be at least 3 characters long.");
            return;
        }

        setUserLoading(true);
        try {
            const res = await adminApi.post("/credentials", {
                current_password: userForm.currentPassword,
                new_username: userForm.newUsername.trim(),
            });
            if (res.data?.success) {
                setUserSuccess("Username updated successfully! Session invalidated. Redirecting to login...");
                setTimeout(async () => {
                    await logout();
                    navigate("/admin/login");
                }, 1500);
            }
        } catch (err) {
            setUserError(err.response?.data?.detail || "Failed updating username.");
        } finally {
            setUserLoading(false);
        }
    };

    const handlePasswordSubmit = async (e) => {
        e.preventDefault();
        setPassError("");
        setPassSuccess("");

        if (!passForm.currentPassword) {
            setPassError("Current password is required.");
            return;
        }
        if (!passForm.newPassword || passForm.newPassword.length < 6) {
            setPassError("New password must be at least 6 characters long.");
            return;
        }
        if (passForm.newPassword !== passForm.confirmPassword) {
            setPassError("New password and confirmation do not match.");
            return;
        }

        setPassLoading(true);
        try {
            const res = await adminApi.post("/credentials", {
                current_password: passForm.currentPassword,
                new_password: passForm.newPassword,
            });
            if (res.data?.success) {
                setPassSuccess("Password updated successfully! Session invalidated. Redirecting to login...");
                setTimeout(async () => {
                    await logout();
                    navigate("/admin/login");
                }, 1500);
            }
        } catch (err) {
            setPassError(err.response?.data?.detail || "Failed updating password.");
        } finally {
            setPassLoading(false);
        }
    };

    return (
        <div className="section-card" style={{ marginTop: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                <div>
                    <h3 className="section-title" style={{ margin: 0 }}>Security & Admin Credentials</h3>
                    <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: "4px 0 0" }}>
                        Manage administrator account security and credentials safely
                    </p>
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                    <button
                        onClick={() => setActiveTab("password")}
                        className={`glass-btn ${activeTab === "password" ? "glass-btn-primary" : "glass-btn-ghost"}`}
                        style={{ padding: "6px 14px", minHeight: "36px", fontSize: "0.8rem" }}
                    >
                        Change Password
                    </button>
                    <button
                        onClick={() => setActiveTab("username")}
                        className={`glass-btn ${activeTab === "username" ? "glass-btn-primary" : "glass-btn-ghost"}`}
                        style={{ padding: "6px 14px", minHeight: "36px", fontSize: "0.8rem" }}
                    >
                        Change Username
                    </button>
                </div>
            </div>

            {activeTab === "password" ? (
                <form onSubmit={handlePasswordSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "480px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            Current Password
                        </label>
                        <input
                            type="password"
                            className="glass-input"
                            style={{ width: "100%" }}
                            value={passForm.currentPassword}
                            onChange={(e) => setPassForm((f) => ({ ...f, currentPassword: e.target.value }))}
                            placeholder="Enter current password"
                            disabled={passLoading}
                        />
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            New Password (min. 6 characters)
                        </label>
                        <input
                            type="password"
                            className="glass-input"
                            style={{ width: "100%" }}
                            value={passForm.newPassword}
                            onChange={(e) => setPassForm((f) => ({ ...f, newPassword: e.target.value }))}
                            placeholder="Enter new password"
                            disabled={passLoading}
                        />
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            Confirm New Password
                        </label>
                        <input
                            type="password"
                            className="glass-input"
                            style={{ width: "100%" }}
                            value={passForm.confirmPassword}
                            onChange={(e) => setPassForm((f) => ({ ...f, confirmPassword: e.target.value }))}
                            placeholder="Re-enter new password"
                            disabled={passLoading}
                        />
                    </div>

                    {passError && (
                        <div style={{ color: "#fca5a5", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "12px", padding: "10px 14px", fontSize: "0.82rem" }}>
                            {passError}
                        </div>
                    )}

                    {passSuccess && (
                        <div style={{ color: "#6ee7b7", background: "rgba(52, 211, 153, 0.12)", border: "1px solid rgba(52, 211, 153, 0.25)", borderRadius: "12px", padding: "10px 14px", fontSize: "0.82rem" }}>
                            {passSuccess}
                        </div>
                    )}

                    <div>
                        <button type="submit" disabled={passLoading} className="glass-btn glass-btn-primary">
                            {passLoading ? "Updating Password..." : "Update Password"}
                        </button>
                    </div>
                </form>
            ) : (
                <form onSubmit={handleUsernameSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "480px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            Current Admin Username
                        </label>
                        <input
                            type="text"
                            className="glass-input"
                            style={{ width: "100%", opacity: 0.6 }}
                            value={currentUsername || "admin"}
                            disabled
                        />
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            New Admin Username
                        </label>
                        <input
                            type="text"
                            className="glass-input"
                            style={{ width: "100%" }}
                            value={userForm.newUsername}
                            onChange={(e) => setUserForm((f) => ({ ...f, newUsername: e.target.value }))}
                            placeholder="Enter new username"
                            disabled={userLoading}
                        />
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                            Current Password (for authorization)
                        </label>
                        <input
                            type="password"
                            className="glass-input"
                            style={{ width: "100%" }}
                            value={userForm.currentPassword}
                            onChange={(e) => setUserForm((f) => ({ ...f, currentPassword: e.target.value }))}
                            placeholder="Enter current password"
                            disabled={userLoading}
                        />
                    </div>

                    {userError && (
                        <div style={{ color: "#fca5a5", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "12px", padding: "10px 14px", fontSize: "0.82rem" }}>
                            {userError}
                        </div>
                    )}

                    {userSuccess && (
                        <div style={{ color: "#6ee7b7", background: "rgba(52, 211, 153, 0.12)", border: "1px solid rgba(52, 211, 153, 0.25)", borderRadius: "12px", padding: "10px 14px", fontSize: "0.82rem" }}>
                            {userSuccess}
                        </div>
                    )}

                    <div>
                        <button type="submit" disabled={userLoading} className="glass-btn glass-btn-primary">
                            {userLoading ? "Updating Username..." : "Update Username"}
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
}
