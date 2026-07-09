function goToSignup() {
    window.location.href = "{{ url_for('sign_up') }}";
}

function gotoSignIn() {
    window.location.href = "{{ url_for('sign_in') }}";
}

function gotohomepage() {
    window.location.href = "{{ url_for('home') }}";
}


function previewImages(event) {
    const preview = document.getElementById("imagePreview");
    preview.innerHTML = "";

    const files = event.target.files;

    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();

        reader.onload = function (e) {
            const col = document.createElement("div");
            col.className = "col-md-3 preview-img";

            col.innerHTML = `
                <img src="${e.target.result}">
                <button type="button" class="remove-btn" onclick="this.parentElement.remove()">×</button>
            `;

            preview.appendChild(col);
        };

        reader.readAsDataURL(files[i]);
    }
}

document.addEventListener("DOMContentLoaded", function () {

    const thumbnailInput = document.getElementById("thumbnailInput");
    const preview = document.getElementById("previewImage");
    const uploadContent = document.getElementById("uploadContent");
    const galleryInput = document.getElementById("images");
    const previewContainer = document.getElementById("imagePreview");

    let galleryFiles = []; // array to keep track of selected files

    // ---------------- Thumbnail Preview ----------------
    if (thumbnailInput) {
        thumbnailInput.addEventListener("change", function (event) {
            const file = event.target.files[0];

            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    preview.src = e.target.result;
                    preview.classList.remove("d-none");
                    uploadContent.classList.add("d-none");
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ---------------- Gallery Preview ----------------
    if (galleryInput) {
        galleryInput.addEventListener("change", function (event) {

            Array.from(event.target.files).forEach(file => {
                galleryFiles.push(file);
            });

            updateGalleryPreview();
        });
    }

    // Function to update gallery preview and remove buttons
    function updateGalleryPreview() {
        previewContainer.innerHTML = "";

        galleryFiles.forEach((file, index) => {
            const reader = new FileReader();

            reader.onload = function (e) {
                const col = document.createElement("div");
                col.className = "col-4 position-relative";

                col.innerHTML = `
                    <img src="${e.target.result}" 
                         class="img-fluid rounded shadow-sm" 
                         style="height:100px; object-fit:cover;">
                    <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-1 remove-btn">&times;</button>
                `;

                // Remove button event
                col.querySelector(".remove-btn").addEventListener("click", function () {
                    galleryFiles.splice(index, 1); // remove file from array
                    updateGalleryPreview();         // re-render preview
                });

                previewContainer.appendChild(col);
            };

            reader.readAsDataURL(file);
        });

        const dataTransfer = new DataTransfer();
        galleryFiles.forEach(f => dataTransfer.items.add(f));
        galleryInput.files = dataTransfer.files;
    }

});


document.addEventListener("DOMContentLoaded", function () {

    const propertyType = document.getElementById("propertyType");
    const rentalFields = document.getElementById("rentalFields");
    const saleFields = document.getElementById("saleFields");

    propertyType.addEventListener("change", function () {

        if (this.value === "Rental") {
            rentalFields.classList.remove("d-none");
            saleFields.classList.add("d-none");
        }
        else if (this.value === "Sale") {
            saleFields.classList.remove("d-none");
            rentalFields.classList.add("d-none");
        }
        else {
            rentalFields.classList.add("d-none");
            saleFields.classList.add("d-none");
        }

    });

});



// ---------------- OTP Verification ----------------//

document.addEventListener("DOMContentLoaded", function () {

    const getOtpBtn = document.getElementById("getOtpBtn");
    const verifyOtpBtn = document.getElementById("verifyOtpBtn");
    const otpSection = document.getElementById("otpSection");
    const submitBtn = document.getElementById("submitBtn");

    if (!getOtpBtn || !verifyOtpBtn) return;

    // 🔹 Get OTP (Email)
    getOtpBtn.addEventListener("click", async () => {

        const email = document.getElementById("ownerEmail").value.trim();

        if (!email || !email.includes("@")) {
            alert("Enter valid email address");
            return;
        }

        getOtpBtn.disabled = true;
        getOtpBtn.innerText = "Sending...";

        try {
            const res = await fetch("/send-otp-property", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });

            const data = await res.json();

            if (data.success) {
                otpSection.classList.remove("d-none");
                document.getElementById("otpMessage").innerHTML =
                    "<span class='text-success fw-semibold'>OTP sent to your email.</span>";
            } else {
                document.getElementById("otpMessage").innerHTML =
                    "<span class='text-danger'>" + data.message + "</span>";
            }
        } catch (err) {
            console.error(err);
            document.getElementById("otpMessage").innerHTML =
                "<span class='text-danger'>Error sending OTP. Try again.</span>";
        }

        getOtpBtn.disabled = false;
        getOtpBtn.innerText = "Get OTP";
    });

    // 🔹 Verify OTP
    verifyOtpBtn.addEventListener("click", async () => {
        const otp = document.getElementById("otpInput").value.trim();
        const email = document.getElementById("ownerEmail").value.trim();

        if (!otp || otp.length !== 6) {
            alert("Enter valid 6-digit OTP");
            return;
        }

        verifyOtpBtn.disabled = true;
        verifyOtpBtn.innerText = "Verifying...";

        try {
            const res = await fetch("/verify-property-otp", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, otp })
            });

            const data = await res.json();

            if (data.success) {
                document.getElementById("otpMessage").innerHTML =
                    "<span class='text-success fw-semibold'>✔ Email verified successfully!</span>";
                submitBtn.disabled = false;
                document.getElementById("ownerEmail").readOnly = true;
                getOtpBtn.disabled = true;
            } else {
                document.getElementById("otpMessage").innerHTML =
                    "<span class='text-danger'>" + data.message + "</span>";
            }
        } catch (err) {
            console.error(err);
            document.getElementById("otpMessage").innerHTML =
                "<span class='text-danger'>Error verifying OTP. Try again.</span>";
        }

        verifyOtpBtn.disabled = false;
        verifyOtpBtn.innerText = "Verify OTP";
    });

});

const getOtpBtn = document.getElementById('getOtpBtn');
const verifyOtpBtn = document.getElementById('verifyOtpBtn');
const otpSection = document.getElementById('otpSection');
const otpInput = document.getElementById('otpInput');
const otpMessage = document.getElementById('otpMessage');
const submitBtn = document.getElementById('submitBtn');
const emailInput = document.getElementById('floatingEmail');
const signupForm = document.getElementById('signupForm');

let otpVerified = false;

// Send OTP
getOtpBtn.addEventListener('click', () => {
    const email = emailInput.value.trim();
    if (!email) { alert("Enter email."); return; }

    fetch(`/send_otp?email=${encodeURIComponent(email)}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                otpSection.classList.remove("d-none");
                otpMessage.textContent = data.message;
                otpMessage.className = "text-success";
            } else {
                otpMessage.textContent = data.message;
                otpMessage.className = "text-danger";
            }
        }).catch(err => console.error(err));
});

// Verify OTP
verifyOtpBtn.addEventListener('click', () => {
    const email = emailInput.value.trim();
    const otp = otpInput.value.trim();
    if (otp.length !== 6) {
        otpMessage.textContent = "Enter a valid 6-digit OTP";
        otpMessage.className = "text-danger";
        return;
    }

    fetch("/verify_otp_ajax", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp })
    }).then(res => res.json())
      .then(data => {
        if (data.status === "success") {
            otpVerified = true;
            otpMessage.textContent = data.message;
            otpMessage.className = "text-success";
            submitBtn.disabled = false;
        } else {
            otpMessage.textContent = data.message;
            otpMessage.className = "text-danger";
            submitBtn.disabled = true;
        }
      }).catch(err => console.error(err));
});

// Submit form
signupForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!otpVerified) { alert("Verify OTP first."); return; }

    const formData = new FormData(signupForm);
    const data = Object.fromEntries(formData.entries());

    fetch("/register_user_ajax", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    }).then(res => res.json())
      .then(data => {
        if (data.status === "success") {
            window.location.href = data.redirect;
        } else {
            alert(data.message);
        }
      }).catch(err => console.error(err));
});