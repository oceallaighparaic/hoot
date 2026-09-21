let socket;

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
        console.log("hollered!");
        console.log(`${data.from}`);
    })
}, false);