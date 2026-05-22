function add_friend(btn) {
    ds = btn.dataset

    let data = new FormData();
    data.append("add_friend_id", ds.friendId);
    data.append("user_id", ds.userId);

    let status;
    fetch(
        add_friend_url,
        {
            method: "POST",
            body: data
        }
    )
    .then(res => {
        status = res.status;
    })
    .then(data => {
        if (status === 200) window.location.reload();
    })
    .catch(err => {
        console.log("Network error.");
    });
}

function remove_friend(btn) {
    ds = btn.dataset

    let data = new FormData();
    data.append("remove_friend_id", ds.friendId);
    data.append("user_id", ds.userId);

    let status;
    fetch(
        remove_friend_url,
        {
            method: "POST",
            body: data
        }
    )
    .then(res => {
        status = res.status
    })
    .then(data => {
        if (status === 204) window.location.reload();
    })
    .catch(err => {
        console.log("Network error.");
    });
}