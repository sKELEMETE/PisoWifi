import Fade from "../animations/Fade";

import InsertCoinView from "./InsertCoinView";
import LoadingView from "./LoadingView";
import ActiveSessionView from "./ActiveSessionView";
import PausedView from "./PausedView";
import ExpiredView from "./ExpiredView";
import ErrorView from "./ErrorView";

export default function PortalView({

    state,

    session,

}) {

    let view;

    switch (state) {

        case "loading":

            view = <LoadingView />;

            break;

        case "insert":

            view = <InsertCoinView />;

            break;

        case "active":

            view = (

                <ActiveSessionView

                    session={session}

                />

            );

            break;

        case "paused":

            view = <PausedView />;

            break;

        case "expired":

            view = <ExpiredView />;

            break;

        default:

            view = <ErrorView />;

    }

    return (

        <Fade>

            {view}

        </Fade>

    );

}
