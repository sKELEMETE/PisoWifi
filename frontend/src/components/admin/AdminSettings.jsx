import { useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import useAdminStore from "../../store/adminStore";

export default function AdminSettings({ currentUsername }) {
    const navigate = useNavigate();
    const logout = useAdminStore((state) => state.logout);

    const [activeTab, setActiveTab] = useState("password");

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
            setUserError("New username must be at least 3 characters.");
            return;
        }

        setUserLoading(true);
        try {
            const res = await adminApi.post("/credentials", {
                current_password: userForm.currentPassword,
                new_username: userForm.newUsername.trim(),
            });
            if (res.data?.success) {
                setUserSuccess("Username updated. Session invalidated — redirecting to login…");
                setTimeout(async () => {
                    await logout();
                    navigate("/admin/login");
                }, 1800);
            }
        } catch (err) {
            setUserError(err.response?.data?.detail || "Failed to update username.");
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
            setPassError("New password must be at least 6 characters.");
            return;
        }
        if (passForm.newPassword !== passForm.confirmPassword) {
            setPassError("Passwords do not match.");
            return;
        }

        setPassLoading(true);
        try {
            const res = await adminApi.post("/credentials", {
                current_password: passForm.currentPassword,
                new_password: passForm.newPassword,
            });
            if (res.data?.success) {
                setPassSuccess("Password updated. Session invalidated — redirecting to login…");
                setTimeout(async () => {
                    await logout();
                    navigate("/admin/login");
                }, 1800);
            }
        } catch (err) {
            setPassError(err.response?.data?.detail || "Failed to update password.");
        } finally {
            setPassLoading(false);
        }
    };

    return (
        <div>
            {/* Settings Header */}
            <div className="section-card-header" style={{ marginBottom: "var(--admin-space-6)" }}>
                <div>
                    <h3 className="section-title">Security &amp; Credentials</h3>
                    <p className="section-subtitle">
                        Manage administrator account access and authentication
                    </p>
                </div>

                {/* Tab Switcher */}
                <div className="admin-tab-group" role="tablist" aria-label="Settings tabs">
                    <button
                        role="tab"
                        aria-selected={activeTab === "password"}
                        onClick={() => {
                            setActiveTab("password");
                            setPassError(""); setPassSuccess("");
                        }}
                        className={`admin-tab-btn${activeTab === "password" ? " active" : ""}`}
                        id="tab-password"
                        aria-controls="panel-password"
                    >
                        Password
                    </button>
                    <button
                        role="tab"
                        aria-selected={activeTab === "username"}
                        onClick={() => {
                            setActiveTab("username");
                            setUserError(""); setUserSuccess("");
                        }}
                        className={`admin-tab-btn${activeTab === "username" ? " active" : ""}`}
                        id="tab-username"
                        aria-controls="panel-username"
                    >
                        Username
                    </button>
                </div>
            </div>

            {/* ── Change Password ── */}
            {activeTab === "password" && (
                <div
                    role="tabpanel"
                    id="panel-password"
                    aria-labelledby="tab-password"
                >
                    <form
                        onSubmit={handlePasswordSubmit}
                        className="admin-form-panel"
                        id="admin-change-password-form"
                        noValidate
                    >
                        <div className="admin-form-group">
                            <label htmlFor="pass-current" className="admin-form-label">
                                Current Password
                            </label>
                            <input
                                id="pass-current"
                                type="password"
                                className="glass-input"
                                placeholder="Enter your current password"
                                value={passForm.currentPassword}
                                onChange={(e) => setPassForm(f => ({ ...f, currentPassword: e.target.value }))}
                                disabled={passLoading}
                                autoComplete="current-password"
                                required
                            />
                        </div>

                        <div className="admin-form-group">
                            <label htmlFor="pass-new" className="admin-form-label">
                                New Password
                            </label>
                            <input
                                id="pass-new"
                                type="password"
                                className="glass-input"
                                placeholder="At least 6 characters"
                                value={passForm.newPassword}
                                onChange={(e) => setPassForm(f => ({ ...f, newPassword: e.target.value }))}
                                disabled={passLoading}
                                autoComplete="new-password"
                                minLength={6}
                                required
                            />
                            <span className="admin-form-hint">Minimum 6 characters required</span>
                        </div>

                        <div className="admin-form-group">
                            <label htmlFor="pass-confirm" className="admin-form-label">
                                Confirm New Password
                            </label>
                            <input
                                id="pass-confirm"
                                type="password"
                                className="glass-input"
                                placeholder="Re-enter new password"
                                value={passForm.confirmPassword}
                                onChange={(e) => setPassForm(f => ({ ...f, confirmPassword: e.target.value }))}
                                disabled={passLoading}
                                autoComplete="new-password"
                                required
                            />
                        </div>

                        {passError && (
                            <div className="admin-alert admin-alert-danger" role="alert">
                                <span className="admin-alert-icon">⚠️</span>
                                <span>{passError}</span>
                            </div>
                        )}

                        {passSuccess && (
                            <div className="admin-alert admin-alert-success" role="status">
                                <span className="admin-alert-icon">✓</span>
                                <span>{passSuccess}</span>
                            </div>
                        )}

                        <div>
                            <button
                                type="submit"
                                id="admin-update-password-btn"
                                disabled={passLoading}
                                className="glass-btn glass-btn-primary"
                            >
                                {passLoading ? "Updating…" : "Update Password"}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* ── Change Username ── */}
            {activeTab === "username" && (
                <div
                    role="tabpanel"
                    id="panel-username"
                    aria-labelledby="tab-username"
                >
                    <form
                        onSubmit={handleUsernameSubmit}
                        className="admin-form-panel"
                        id="admin-change-username-form"
                        noValidate
                    >
                        <div className="admin-form-group">
                            <label htmlFor="user-current" className="admin-form-label">
                                Current Username
                            </label>
                            <input
                                id="user-current"
                                type="text"
                                className="glass-input"
                                value={currentUsername || "admin"}
                                disabled
                                aria-readonly="true"
                                style={{ opacity: 0.5 }}
                            />
                        </div>

                        <div className="admin-form-group">
                            <label htmlFor="user-new" className="admin-form-label">
                                New Username
                            </label>
                            <input
                                id="user-new"
                                type="text"
                                className="glass-input"
                                placeholder="Enter new username"
                                value={userForm.newUsername}
                                onChange={(e) => setUserForm(f => ({ ...f, newUsername: e.target.value }))}
                                disabled={userLoading}
                                minLength={3}
                                required
                            />
                            <span className="admin-form-hint">Minimum 3 characters required</span>
                        </div>

                        <div className="admin-form-group">
                            <label htmlFor="user-pass" className="admin-form-label">
                                Current Password (for authorization)
                            </label>
                            <input
                                id="user-pass"
                                type="password"
                                className="glass-input"
                                placeholder="Enter your current password"
                                value={userForm.currentPassword}
                                onChange={(e) => setUserForm(f => ({ ...f, currentPassword: e.target.value }))}
                                disabled={userLoading}
                                autoComplete="current-password"
                                required
                            />
                        </div>

                        {userError && (
                            <div className="admin-alert admin-alert-danger" role="alert">
                                <span className="admin-alert-icon">⚠️</span>
                                <span>{userError}</span>
                            </div>
                        )}

                        {userSuccess && (
                            <div className="admin-alert admin-alert-success" role="status">
                                <span className="admin-alert-icon">✓</span>
                                <span>{userSuccess}</span>
                            </div>
                        )}

                        <div>
                            <button
                                type="submit"
                                id="admin-update-username-btn"
                                disabled={userLoading}
                                className="glass-btn glass-btn-primary"
                            >
                                {userLoading ? "Updating…" : "Update Username"}
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
}
