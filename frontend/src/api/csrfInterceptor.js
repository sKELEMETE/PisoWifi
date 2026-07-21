export function addCsrfInterceptor(api) {
    api.interceptors.request.use(
        (config) => {
            if (config.method && ["post", "put", "patch", "delete"].includes(config.method)) {
                const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
                if (match) {
                    config.headers["X-CSRF-Token"] = decodeURIComponent(match[1]);
                }
            }
            return config;
        },
        (error) => Promise.reject(error)
    );
}
