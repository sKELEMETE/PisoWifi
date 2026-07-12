export default function Button({

    children,

    onClick,

    variant = "primary",

    disabled = false,

    type = "button",

}) {

    return (

        <button

            type={type}

            disabled={disabled}

            onClick={onClick}

            className={`btn btn-${variant}`}

        >

            <span>

                {children}

            </span>

        </button>

    );

}
