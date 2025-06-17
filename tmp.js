async function sendMessage() {
    const button = document.getElementById('buttonSend');
    const chatBody = document.getElementById('chatBody');
    let userMessage = ''; // Default message if no custom input
    
    // Disable the button
    button.disabled = true;
    button.textContent = "Reading...";
    
    // Get the image data (either from file upload or receivedImage)
    let base64ImageData = null;
    const fileInput = document.getElementById('imageUpload');
    
    if (fileInput.files.length > 0) {
        // Image from file input
        const file = fileInput.files[0];
        console.log(file)
        base64ImageData = await fileToBase64(file);
        // console.log(base64ImageData);
        
    } else if (receivedImage) {
        // Image from URL parameter
        const img = new Image();
        img.src = decodeURIComponent(receivedImage);
        console.log(img.src);
        base64ImageData = await imageUrlToBase64(img.src);
        // // base64ImageData = decodeURIComponent(receivedImage).split(',')[1]; // Extract base64 data
        // base64ImageData = await fileToBase64(img.src); // Extract base64 data
        // console.log(base64ImageData);
    } else {
        // Handle the error: No image provided
        handleErrorMessage("Please upload an image before sending.");
        return;
    }
    let messageContent = null;
    // Send the base64 image data to the server for processing
    const post_response = await fetch('http://203.185.131.205/vision-world/process-image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        },
        body: JSON.stringify({
            image: base64ImageData,
            threshold: 500,
            contrast_level: 1.30
        })
    });
    
    if (post_response.ok) {
        const processedImageData = await post_response.json();
        console.log(processedImageData.text_response);
        messageContent = [
            {
                "type": "text",
                "text": "ข้อความในภาพนี้" // Use userMessage or a default prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": `data:image/jpeg;base64,${processedImageData.image}`
                }
            }
        ];
    } else {
        handleErrorMessage("Error processing image.");
        return;
    }
    console.log(messageContent);

    // Construct the request body
    const requestBody = {
        "messages": [
            {
                "role": "system", 
                "content": ""
            },
            {

                "role": "user",
                "content": messageContent
            }
        ],
        "model": "nectec/Pathumma-vision-ocr-lora-dev"
    };

    // Send the request to the new API endpoint
    try {
        const response = await fetch('http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions', { // Replace with your new endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json' // Add any other necessary headers
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status}`);
        }

        const data = await response.json();

        // Display the bot's response
        console.log(data.choices[0].message.content);
        
        displayBotMessage(data.choices[0].message.content); // Assuming the response has an 'answer' field

    } catch (error) {
        console.error('Error:', error);
        handleErrorMessage(`An error occurred while sending the message: ${error}`);
    } finally {
        // Re-enable the button
        button.disabled = false;
        button.textContent = "Send";

        // Scroll to the bottom of the chat
        setTimeout(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
        }, 0);
    }
}

// Helper function to convert a file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]); // Extract base64 data
        reader.onerror = error => reject(error);
    });
}

async function imageUrlToBase64(url) {
    try {
        const response = await fetch(url);
        const blob = await response.blob();

        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(',')[1]); // Get the Base64 string without the metadata
            reader.onerror = reject;
            reader.readAsDataURL(blob); // Converts the blob to Base64
        });
    } catch (error) {
        console.error('Error converting image to Base64:', error);
        throw error;
    }
}

function convertNewlinesToBr(text) {
    return text.replace(/\n/g, "<br>");
}

// Helper function to display bot messages
function displayBotMessage(message) {
    const botMessageDiv = document.createElement('div');
    botMessageDiv.classList.add('message', 'bot');
    // botMessageDiv.innerHTML = `<div class="text">${message}</div>`;
    botMessageDiv.innerHTML = convertNewlinesToBr(`<div class="text">${message}</div>`);
    chatBody.appendChild(botMessageDiv);
}

// Helper function to handle errors and display error messages
function handleErrorMessage(message) {
    const errorMessageDiv = document.createElement('div');
    errorMessageDiv.classList.add('message', 'bot', 'error');
    errorMessageDiv.innerHTML = `<div class="text">${message}</div>`;
    chatBody.appendChild(errorMessageDiv);
}



// Get example image form home
const urlParams = new URLSearchParams(window.location.search);
const receivedImage = urlParams.get('image');

// input file
const uploadContainer = document.querySelector('.upload-container');
const imageUploadInput = document.getElementById('imageUpload');
const previewArea = document.getElementById('previewArea');

// show example image form home
 if (receivedImage) {
    
    previewArea.innerHTML = `<img src="${decodeURIComponent(receivedImage)}" alt="Uploaded Image">`;
    const img = new Image();
    img.src = decodeURIComponent(receivedImage)
    sendMessage();

    console.log("Done Received mode ...")
} else {
    console.log("Skip Received mode ...")
}

// open file dialog 
uploadContainer.addEventListener('click', () => {
    imageUploadInput.click();
});

imageUploadInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (previewArea.lastChild) {
        previewArea.innerHTML = `<p class="placeholder">Drop an image here or click to upload</p>`
    }
    if (file) {
        displayImage(file);
    } else {
        imageUploadInput.removeEventListener('change', event)
    }
});

function displayImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        previewArea.innerHTML = `<img src="${e.target.result}" alt="Uploaded Image">`;
    };
    reader.readAsDataURL(file);
}