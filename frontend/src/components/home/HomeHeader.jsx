import branding from "../../config/branding";

export default function HomeHeader() {
    return (
        <>
            <h1>{branding.appName}</h1>

            <p>
                {branding.tagline}
            </p>

            <hr />
        </>
    );
}
