import api from "./axios";

export async function getCoinStatus() {
    const { data } = await api.get("/coin/status");
    return data;
}
