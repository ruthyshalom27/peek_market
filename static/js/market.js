document.addEventListener("DOMContentLoaded", function () {

    console.log("Peek Market WebSocket starting...");

    if (typeof io === "undefined") {

        console.error("Socket.IO library not loaded.");

        return;
    }


    const socket = io();


    const connectionText =
        document.getElementById("connectionText");


    const connectionDot =
        document.getElementById("connectionDot");


    /*
     * CONNECTED
     */

    socket.on("connect", function () {

        console.log(
            "✓ Market WebSocket connected"
        );


        if (connectionText) {

            connectionText.textContent =
                "Market stream connected";

        }


        if (connectionDot) {

            connectionDot.style.background =
                "#58a878";

        }

    });


    /*
     * DISCONNECTED
     */

    socket.on("disconnect", function () {

        console.log(
            "Market WebSocket disconnected"
        );


        if (connectionText) {

            connectionText.textContent =
                "Market stream disconnected";

        }


        if (connectionDot) {

            connectionDot.style.background =
                "#c76068";

        }

    });


    /*
     * CONNECTION STATUS
     */

    socket.on(
        "connection_status",
        function (data) {

            console.log(
                "Connection status:",
                data
            );

        }
    );


    /*
     * MARKET UPDATE
     */

    socket.on(
        "market_update",
        function (data) {

            console.log(
                "Market update:",
                data
            );


            const short =
                data.short ||
                data.short_symbol ||
                String(
                    data.symbol || ""
                ).replace(".NS", "");


            /*
             * PRICE
             */

            const priceElement =
                document.querySelector(
                    '[data-price="' +
                    short +
                    '"]'
                );


            if (
                priceElement &&
                data.price !== undefined
            ) {

                priceElement.textContent =
                    "₹" +
                    Number(data.price)
                        .toFixed(2);

            }


            /*
             * CHANGE
             */

            const changeElement =
                document.querySelector(
                    '[data-change="' +
                    short +
                    '"]'
                );


            if (
                changeElement &&
                data.change !== undefined
            ) {

                const change =
                    Number(data.change);


                changeElement.textContent =
                    (change >= 0
                        ? "↑ "
                        : "↓ ") +
                    change.toFixed(2) +
                    "%";


                changeElement.classList.remove(
                    "positive",
                    "negative"
                );


                changeElement.classList.add(
                    change >= 0
                        ? "positive"
                        : "negative"
                );

            }


            /*
             * CARD FLASH
             */

            const card =
                document.getElementById(
                    "stock-" + short
                );


            if (card) {

                card.classList.add(
                    "market-updated"
                );


                setTimeout(
                    function () {

                        card.classList.remove(
                            "market-updated"
                        );

                    },
                    500
                );

            }

        }
    );

});