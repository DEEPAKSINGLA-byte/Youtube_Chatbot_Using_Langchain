from flask import Flask,render_template,request,jsonify
from rag import ask_rag
app=Flask(__name__)
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/ask",methods=["POST"])
def ask():
    data=request.get_json()
    video=data["video_id"]
    question=data["question"]
    print("Video ID:", video)
    print("Question:", question)
    answer=ask_rag(video,question)
    return jsonify({
        "answer":answer
    })
if __name__ == "__main__":
    app.run(debug=True)