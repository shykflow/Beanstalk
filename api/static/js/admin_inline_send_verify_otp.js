function getCookie(cookieName) {
    const name = cookieName + "=";
    // Cookies are a long string of "asdf=123;qwerty=jkl;"
    const cookiesStr = decodeURIComponent(document.cookie);
    // Separate them
    let cookies = cookiesStr.split(';');
    // Sometimes cookies have extra white space around them
    cookies = cookies.map((c) => c.trim());
    for (let cookie of cookies) {
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length, cookie.length);
        }
    }
    return "";
}

async function send_verification_otp(mfa_config_id) {
    const protocol = window.location.protocol;
    const host = window.location.host;
    const endpoint = `${protocol}//${host}/users/admin_send_verification_otp/`;
    const csrftoken = getCookie('csrftoken');
    const button = document.getElementById(`send-verify-button-${mfa_config_id}`);
    button.classList.add('sending');
    try {
        const response = await fetch(
            endpoint,
            {
                method: "POST",
                mode: 'cors',
                credentials: "same-origin",
                headers: {
                    'Accept': 'application/json',
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                cache: 'no-cache',
                body: JSON.stringify({
                    'id': mfa_config_id,
                }),
            }
        );
        if (response.ok) {
            const jsonData = await response.json();
            const hint = jsonData['hint']
            const timeoutLabel = jsonData['timeout_label']
            const alertMsg = `Code was sent to ${hint}, ` +
                `and will expire in ${timeoutLabel}.\n\n` +
                'Please enter the code that was sent and save this page.';
            alert(alertMsg);
        }
        else {
            const jsonData = await response.json();
            alert(jsonData['error']);
        }
    }
    catch (e) {
        alert('Something went wrong');
    }
    button.classList.remove('sending')
    return false;
}
