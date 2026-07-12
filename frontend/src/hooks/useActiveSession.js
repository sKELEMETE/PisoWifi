import useSessionStore from "../store/sessionStore";

export default function useActiveSession() {

    const {

        session,

        loading,

        error,

    } = useSessionStore();

    return {

        session,

        loading,

        error,

    };

}

