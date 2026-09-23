let socket;
let active_hollers = new Map();
const len = 5000

document.addEventListener("DOMContentLoaded", () => {
    console.log("studies have shown that Hi");
    socket = io(); // connect to server

    socket.on("server_connection", (data) => {
        console.log("CONNECTION");
        // console.log(data.data);
    });

    socket.on("server_response", (data) => {
        // console.log(`${data.message}`);
    });

    socket.on("holler", (data) => {
        if(typeof friend_id !== "undefined") {
            if(friend_id == data.from_id) return;
        }

        function start_timer(from, notif) {
            return setTimeout(() => {notif.remove(); active_hollers.delete(from)}, len);
        }

        // refresh existing notif
        let existing_holler = active_hollers.get(data.from);
        if(existing_holler) {
            clearTimeout(existing_holler.timeout);
            existing_holler.timeout = start_timer(data.from, existing_holler.notif);
            return;
        }

        // new notif
        let tmp = document.querySelector("#notification_hub template");
        let notif = tmp.content.firstElementChild.cloneNode(true);
        notif.querySelector("p").textContent = `from ${data.from}`;
        notif.href = chat_url + `${data.from_id}`
        document.getElementById("notification_hub").appendChild(notif);
        
        active_hollers.set(data.from, {notif, timeout: start_timer(data.from, notif)});
    })
}, false);