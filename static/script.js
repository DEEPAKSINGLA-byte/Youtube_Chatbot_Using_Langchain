const button = document.getElementById("ask-btn");
button.addEventListener("click", askQuestion);

async function askQuestion() {

    const video = document.getElementById("video").value;
    const question = document.getElementById("question").value;
    document.getElementById("answer").innerText = "Thinking...";
    button.disabled = true;
    button.innerText = "Thinking...";

    try {
        const response = await fetch("/ask", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                video_id: video,
                question: question

            })

        });

        const data = await response.json();

        document.getElementById("answer").innerText =
            data.answer;
    }
    catch(err){

        document.getElementById("answer").innerText =
            "Something went wrong.";

    }

    button.disabled = false;
    button.innerText = "Ask";
}
