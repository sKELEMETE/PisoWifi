import Button from "../common/Button";

export default function InsertCoinView() {

    return (

        <div className="portal-view">

            <div className="coin-icon">

                🪙

            </div>

            <h2>

                Ready to Connect

            </h2>

            <p>

                Insert coins into the machine.

                <br />

                Your internet starts automatically.

            </p>

            <Button>

                Waiting for Coin...

            </Button>

        </div>

    );

}
