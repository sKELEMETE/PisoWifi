import ConnectionBadge from "../common/ConnectionBadge";
import usePortalStore from "../../store/portalStore";
import PortalState from "../../constants/portalState";
import branding from "../../config/branding";

export default function Header() {
    const portalState = usePortalStore(state => state.portalState);
    const isInternetAuthorized = portalState === PortalState.ACTIVE;

    const renderLogo = () => {
        if (!branding.logo) return null;
        if (branding.logo.startsWith('/') || branding.logo.startsWith('http') || branding.logo.includes('.')) {
            return <img src={branding.logo} alt="Logo" style={{ maxWidth: "80%", maxHeight: "80%" }} />;
        }
        return branding.logo;
    };

    return (
        <header className="portal-header">
            <div className="logo-wrapper">
                {/* <div className="logo-circle"> */}
                   {/* {renderLogo()} */}
                {/* </div> */}
                <div>
                    <p className="logo-caption">
                        {branding.tagline}
                    </p>
                    <h1 style={{ fontSize: "1.8rem" }}>
                        {branding.appName}
                    </h1>
                </div>
            </div>

            <div className="status-container">
                <div className="status-item">
                    <span className="status-label">WiFi:</span>
                    <ConnectionBadge
                        online={true}
                        text="Connected"
                    />
                </div>
                <div className="status-item">
                    <span className="status-label">Internet:</span>
                    <ConnectionBadge
                        online={isInternetAuthorized}
                        text={isInternetAuthorized ? "Available" : "Blocked"}
                    />
                </div>
            </div>
        </header>
    );
}
