export default function Input({
    value,
    onChange,
    placeholder = "",
    type = "text",
}) {
    return (
        <input
            type={type}
            value={value}
            placeholder={placeholder}
            onChange={onChange}
            style={{
                width: "100%",
                padding: "12px",
                fontSize: "16px",
                borderRadius: "6px",
                border: "1px solid #ccc",
            }}
        />
    );
}
