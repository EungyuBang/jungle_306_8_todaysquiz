function register() {
  let inputId = $("#id-input").val();
  let inputPw = $("#pw-input").val();
  let inputName = $("#name-input").val();

  $.ajax({
    type: "POST",
    url: "/register",
    data: { inputId: inputId, inputPw: inputPw, inputName: inputName },
    success: function (response) {
      if (response["result"] == "success") {
        alert("회원가입 성공!");
        window.location.href = "/";
      } else {
        alert(response["msg"]);
      }
    },
  });
}

function login() {
  let userId = $("#id-input").val();
  let userPw = $("#pw-input").val();

  $.ajax({
    type: "POST",
    url: "/login",
    data: { userId: userId, userPw: userPw },
    success: function (response) {
      if (response["result"] == "success") {
        alert("로그인 성공!");
        window.location.href = "afterlogin";
      } else {
        alert(response["msg"]);
      }
    },
  });
}

function addquiz() {
  let category = selectedLang;
  let quiz_grade = selectedLevel;
  let quiz_sentence = $("#quiz_sentence").val();
  let quiz_code = $("#quiz_code").val();
  let answer = $("#answer").val();

  $.ajax({
    type: "POST",
    url: "/addquiz",
    data: {
      category: category,
      quiz_grade: quiz_grade,
      quiz_sentence: quiz_sentence,
      quiz_code: quiz_code,
      answer: answer,
    },
    success: function (response) {
      if (response["result"] == "success") {
        alert("추가 성공!");
        window.location.href = "afterlogin";
      } else {
        alert(response["msg"]);
      }
    },
  });
}

// ===== 신고 기능 =====
function complaint(btn) {
  const quizDiv = $(btn).closest(".quiz-card");
  const section = quizDiv.parent();
  const qid = quizDiv.data("id");
  if (!qid) return alert("문제 ID를 찾을 수 없습니다.");

  $.post(`/quiz/complaint/${qid}`, {}, function (res) {
    alert(res.msg || "신고 완료");

    const removedNum = res.quiz_num;
    section.remove();

    const excludeIds = $("form .quiz-card")
      .map(function () { return $(this).data("id"); })
      .get();

    // ✅ 추가: 현재 폼에서 category/grade 읽어서 함께 보냄
    const form = $("#quiz-form");
    const category = form.data("category");
    const grade = form.data("grade");

    $.get(
      `/quiz/next?start_num=${removedNum}` +
      `&exclude=${excludeIds.join(",")}` +
      `&category=${encodeURIComponent(category)}` +
      `&grade=${encodeURIComponent(grade)}`,
      function (data) {
        if (!data.length) return;
        const q = data[0];
        const blanksInputs = q.blanks.map((b, i) =>
          `<input name="answer-${q._id}-${i+1}" placeholder="정답을 입력하세요." required
                  class="w-full bg-transparent outline-none placeholder-stone-400 border-0 border-b-2 border-main/40 focus:border-main py-2" />`
        ).join("");

        const newSection = $(`
          <section class="space-y-3">
            <div class="flex items-center justify-between quiz-card" data-id="${q._id}" data-num="${q.quiz_num}">
              <h2 class="font-semibold">${q.quiz_sentence}</h2>
              <div class="flex items-center gap-2">
                <button type="button" class="inline-flex items-center gap-1 rounded-md border border-main/50 text-main px-3 py-1.5 text-sm hover:bg-main/5">
                  북마크
                </button>
                <button type="button" class="inline-flex items-center gap-1 rounded-md border border-main/50 text-main px-3 py-1.5 text-sm hover:bg-main/5" onclick="complaint(this)">
                  신고하기
                </button>
              </div>
            </div>
            <pre class="bg-stone-200 rounded-md w-full h-48 p-4 overflow-auto text-sm leading-6 text-stone-800"><code>${q.quiz_code}</code></pre>
            <input type="hidden" name="quiz_ids[]" value="${q._id}" />
            <div class="space-y-3">${blanksInputs}</div>
          </section>
        `);

        newSection.insertBefore($("form button[type='submit']"));

        // 번호 다시 매기기
        $("form section").each(function (i) {
          const sentence = $(this).find("h2").text().split(". ")[1] || $(this).find("h2").text();
          $(this).find("h2").html(`${i + 1}. ${sentence}`);
        });
      }
    );
  });
}

$(document).on("click", ".bookmark-btn", function () {
  const btn = $(this);
  const quizId = btn.data("quiz"); // _id 값
  console.log("클릭된 퀴즈 ID:", quizId); // 이 로그가 빈 문자열인지 확인

  $.post("/toggle_bookmark", { quiz_id: quizId }, function (res) {
    console.log("서버 응답:", res);
    if (res.result === "added") {
      btn.css({ background: "white", color: "#a57a62" });
    } else if (res.result === "removed") {
      btn.css({ background: "#a57a62", color: "white" });
    }
  }).fail(function (jqXHR, textStatus, errorThrown) {
    console.log("요청 실패:", textStatus, errorThrown);
  });
});
