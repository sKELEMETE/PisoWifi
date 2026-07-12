export function formatDuration(seconds) {

    const total = Math.max(0, Number(seconds) || 0);

    const hours = Math.floor(total / 3600);

    const minutes = Math.floor((total % 3600) / 60);

    const secs = total % 60;

    return [

        String(hours).padStart(2, "0"),

        String(minutes).padStart(2, "0"),

        String(secs).padStart(2, "0"),

    ].join(":");

}

