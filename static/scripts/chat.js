let socket;
let chat;
let txt;

let sender_chat;
let receiver_chat;
let save_timer;

document.addEventListener("DOMContentLoaded", () => {
    txt = document.querySelector("#chat-input");
    txt.addEventListener('input', send_message, false);
    sender_chat = document.querySelector("#sender_box p");
    receiver_chat = document.querySelector("#receiver_box p");

    for (msg of messages) {
        if (msg.sender_id == userId) {
            sender_chat.textContent = msg.message;
        } else {
            receiver_chat.textContent = msg.message;
        }
    }

    socket = io(); // connects to server

    socket.on("server_connection", (data) => {
        console.log(`${data.data}`);
    });

    socket.on("server_response", (data) => {
        if (data.sender_id == userId) {
            sender_chat.textContent = data.message;
        } else {
            receiver_chat.textContent = data.message;
        }
    });

    socket.emit("open_chat", { 
        ids:[userId, ...recipientIds] 
    });
}, false);

function send_message(e) {
    if (!txt.value.trim()) return;

    socket.emit("send_key", { 
        message: txt.value, sender_id:`${userId}`, ids:[userId, ...recipientIds] 
    }); 

    if (save_timer) clearTimeout(save_timer);
    save_timer = setTimeout(() => {
        socket.emit("save_message", {
            message: txt.value, sender_id:`${userId}`, ids:[userId, ...recipientIds]
        });
        console.log(`Saved: ${txt.value}`);
    }, 300);
}

window.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        send_message();
        txt.value = "";
    }
});