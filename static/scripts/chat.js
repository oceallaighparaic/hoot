let socket;
let chat;
let txt;

document.addEventListener("DOMContentLoaded", () => {
    socket = io(); // connects to server

    socket.on("server_connection", (data) => {
        console.log(`${data.data}`);
    });

    socket.on("server_response", (data) => {
        console.log(`Server sent:`);
        console.log(data.message);
        console.log(`SenderID: ${data.sender_id}`);
        console.log(`RecipientID: ${data.recipient_id}`);

        chat.appendChild(create_message_article(0, data.message, data.sender_id, data.recipient_id, ""));
    });

    txt = document.querySelector("#chat-input");
    chat = document.querySelector("#chat");

    for (msg of messages)
        chat.appendChild(create_message_article(msg.id, msg.message, msg.sender_id, msg.user_id, msg.sent_at));

    socket.emit("open_chat", { ids:[userId, ...recipientIds] });
}, false);

function create_message_article(id, value, sender_id, user_id, sent_at) {
    /** 
     *  <article class="{% if msg.sender_id == g.user_id %}sent_message{% else %}received_message{% endif %}" id="message_{{ msg.id }}">
     *      <aside>{{ msg.sent_at }}</aside>
     *      <p>message_{{ msg.id }}</p>
     *      <p>{{ msg.message }}</p>
     *  </article> 
     * */

    let art = document.createElement("article");
    art.className = sender_id === userId ? "sent_message" : "received_message";
    art.id = `message-${id}`
    
    let aside = document.createElement("aside");
    aside.innerHTML = `${sent_at}`;
    art.appendChild(aside);

    let msg_id = document.createElement("p");
    msg_id.innerHTML = `${id}`;
    art.appendChild(msg_id);

    let msg_el = document.createElement("p");
    msg_el.innerHTML = `${value}`;
    art.appendChild(msg_el);

    return art; 
}

function send_message() {
    if (!txt.value.trim()) return;

    socket.emit("send_message", { message:txt.value, sender_id:`${userId}`, ids:[userId, ...recipientIds] });
    txt.value = "";
}