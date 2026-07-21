import axios from "axios";
import api from "./client";
import { addCsrfInterceptor } from "./csrfInterceptor";

const voucherApi = axios.create({
    baseURL: "/api/admin/vouchers",
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

addCsrfInterceptor(voucherApi);

export const redeemVoucher = async (code, mac) => {
    const response = await api.post("/voucher/redeem", { code, mac });
    return response.data;
};

export const createVoucher = async (minutes, expiresAt = null) => {
    const payload = { minutes: Number(minutes) };
    if (expiresAt) payload.expires_at = expiresAt;
    const response = await voucherApi.post("", payload);
    return response.data;
};

export const createVouchersBulk = async (count, minutes, expiresAt = null) => {
    const payload = { count: Number(count), minutes: Number(minutes) };
    if (expiresAt) payload.expires_at = expiresAt;
    const response = await voucherApi.post("/bulk", payload);
    return response.data;
};

export const listVouchers = async ({ status, limit = 50, offset = 0, orderBy = "created_at", orderDesc = true } = {}) => {
    const params = new URLSearchParams();
    if (status) params.append("status_filter", status);
    params.append("limit", String(limit));
    params.append("offset", String(offset));
    params.append("order_by", orderBy);
    params.append("order_desc", String(orderDesc));
    const response = await voucherApi.get("", { params });
    return response.data;
};

export const getVoucherStats = async () => {
    const response = await voucherApi.get("/stats");
    return response.data;
};

export const getVoucher = async (voucherId) => {
    const response = await voucherApi.get(`/${voucherId}`);
    return response.data;
};

export const deleteVoucher = async (voucherId) => {
    const response = await voucherApi.delete(`/${voucherId}`);
    return response.data;
};

export const expireVoucher = async (voucherId) => {
    const response = await voucherApi.post(`/${voucherId}/expire`);
    return response.data;
};

export const exportVouchers = async (format = "csv", status = null) => {
    const params = new URLSearchParams({ format });
    if (status) params.append("status_filter", status);
    const response = await voucherApi.get("/export", { params, responseType: "blob" });
    return response;
};

export default voucherApi;