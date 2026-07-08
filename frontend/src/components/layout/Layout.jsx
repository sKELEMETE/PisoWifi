import Navbar from "./Navbar";
import Footer from "./Footer";

export default function Layout({ children }) {
    return (
        <>
            <Navbar />

            <main
                style={{
                    padding: "20px",
                    minHeight: "80vh",
                }}
            >
                {children}
            </main>

            <Footer />
        </>
    );
}
