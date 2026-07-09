const getOtpBtn = document.getElementById('getOtpBtn');
const verifyOtpBtn = document.getElementById('verifyOtpBtn');
const otpSection = document.getElementById('otpSection');
const otpInput = document.getElementById('otpInput');
const otpMessage = document.getElementById('otpMessage');
const submitBtn = document.getElementById('submitBtn');
const emailInput = document.getElementById('floatingEmail');
const signupForm = document.getElementById('agentSignupForm');

let otpVerified = false;

/* Restrict OTP input to numbers */
otpInput.addEventListener("input", () => {
    otpInput.value = otpInput.value.replace(/\D/g, "");
});

/* ---------------- SEND OTP ---------------- */

getOtpBtn.addEventListener('click', () => {

    const email = emailInput.value.trim();

    if (!email) {
        alert("Enter email first.");
        return;
    }

    getOtpBtn.disabled = true;
    getOtpBtn.innerText = "Sending OTP...";

    fetch(`/send_otp?email=${encodeURIComponent(email)}`)
        .then(res => res.json())
        .then(data => {

            if (data.status === "success") {

                otpSection.classList.remove("d-none");

                otpMessage.textContent = data.message;
                otpMessage.className = "text-success";

                emailInput.readOnly = true;     // prevent email change
                otpInput.focus();               // auto focus

                getOtpBtn.innerText = "Resend OTP";
            } else {

                otpMessage.textContent = data.message;
                otpMessage.className = "text-danger";

                getOtpBtn.innerText = "Get OTP";
            }

            getOtpBtn.disabled = false;

        })
        .catch(err => {
            console.error(err);
            getOtpBtn.disabled = false;
            getOtpBtn.innerText = "Get OTP";
        });
});


/* ---------------- VERIFY OTP ---------------- */

verifyOtpBtn.addEventListener('click', () => {

    const email = emailInput.value.trim();
    const otp = otpInput.value.trim();

    if (otp.length !== 6) {
        otpMessage.textContent = "Enter a valid 6-digit OTP";
        otpMessage.className = "text-danger";
        return;
    }

    verifyOtpBtn.disabled = true;
    verifyOtpBtn.innerText = "Verifying...";

    fetch("/verify_otp_ajax", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp })
    })
    .then(res => res.json())
    .then(data => {

        if (data.status === "success") {

            otpVerified = true;

            otpMessage.textContent = "✓ " + data.message;
            otpMessage.className = "text-success";

            submitBtn.disabled = false;

            verifyOtpBtn.innerText = "Verified";
            verifyOtpBtn.classList.remove("btn-success");
            verifyOtpBtn.classList.add("btn-secondary");

        } else {

            otpMessage.textContent = data.message;
            otpMessage.className = "text-danger";

            submitBtn.disabled = true;

            verifyOtpBtn.innerText = "Verify OTP";
            verifyOtpBtn.disabled = false;
        }

    })
    .catch(err => {
        console.error(err);
        verifyOtpBtn.innerText = "Verify OTP";
        verifyOtpBtn.disabled = false;
    });
});


/* ---------------- SUBMIT FORM ---------------- */

signupForm.addEventListener('submit', (e) => {

    e.preventDefault();

    if (!otpVerified) {
        alert("Please verify OTP first.");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = "Registering...";

    const formData = new FormData(signupForm);

    fetch("/register_agent_ajax", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        if (data.status === "success") {
            submitBtn.innerText = "Success ✓";

            setTimeout(() => {
                window.location.href = data.redirect;
            }, 800);

        } else {
            alert(data.message);
            submitBtn.disabled = false;
            submitBtn.innerText = "Register as Agent";
        }

    })
    .catch(err => {
        console.error(err);
        submitBtn.disabled = false;
        submitBtn.innerText = "Register as Agent";
    });

});