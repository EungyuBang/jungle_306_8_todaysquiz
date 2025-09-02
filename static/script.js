function togglePostingBox() {
  const box = $("#postingBox");
  box.toggle();
  if (box.is(":visible")) {
    $("#btn-text-box").text("포스팅박스 닫기");
  } else {
    $("#btn-text-box").text("포스팅박스 열기");
  }
}

$(document).ready(function () {
  $("#card-container").html("");
  showArticles();
});

function postArticle() {
  // 1. 유저가 입력한 데이터를 #post-url과 #post-comment에서 가져오기
  let url = $("#post-url").val();
  let comment = $("#post-comment").val();

  // 2. memo에 POST 방식으로 메모 생성 요청하기
  $.ajax({
    type: "POST", // POST 방식으로 요청하겠다.
    url: "/memo", // /memo라는 url에 요청하겠다.
    data: { url_give: url, comment_give: comment }, // 데이터를 주는 방법
    success: function (response) {
      // 성공하면
      if (response["result"] == "success") {
        alert("포스팅 성공!");
        // 3. 성공 시 페이지 새로고침하기
        window.location.reload();
      } else {
        alert("서버 오류!");
      }
    },
  });
}

function showArticles() {
  $.ajax({
    type: "GET",
    url: "/memo",
    data: {},
    success: function (response) {
      let articles = response["articles"];
      for (let i = 0; i < articles.length; i++) {
        makeCard(
          articles[i]["image"],
          articles[i]["url"],
          articles[i]["title"],
          articles[i]["desc"],
          articles[i]["comment"]
        );
      }
    },
  });
}

function makeCard(image, url, title, desc, comment) {
  let temp_html = `<div class="card">
    <img src="${image}" class="card-img-top" alt="이미지를 불러올 수 없습니다.">
      <div class="card-body">
        <a href="${url}" target="_blank" class="card--title">${title}</a>
        <p class="card--text">${desc}</p>
        <p class="card-comment">${comment}</p>
      </div>
  </div>`;
  {
    /* let temp_html = `<div class="card">
                        <img class="card-img-top" src="${image}" alt="Card image cap">
                        <div class="card-body">
                        <a href="${url}" target="_blank" class="card-title">${title}</a>
                        <p class="card-text">${desc}</p>
                        <p class="card-text comment">${comment}</p>
                        </div>
                    </div>`; */
  }
  $("#card-container").append(temp_html);
}

// 모든 아코디언 제목 요소를 선택합니다. -> mypage에서 문제들 온오프
const accordionTitles = document.querySelectorAll(".accordion-title");

accordionTitles.forEach((title) => {
  title.addEventListener("click", () => {
    // 클릭된 제목의 부모 요소(전체 아이템)를 가져옵니다.
    const parentItem = title.parentElement;

    // 부모 요소에 'active' 클래스를 토글합니다.
    parentItem.classList.toggle("active");
  });
});

function signup_2() {
  // 1. 유저가 입력한 데이터를 #post-url과 #post-comment에서 가져오기
  let ID = $("#ID-input").val();
  let PW = $("#PW-input").val();
  let NAME = $("#NAME-input").val();


  $.ajax({
    type: "POST",
    url: "/signup_2",
    data: { ID_give: ID, PW_give: PW, NAME_give: NAME },
    success: function (response) {
      // 성공하면
      if (response["result"] == "success") {
        alert("회원가입 성공!");
        window.location.href = "/";
      } else {
        alert(response['msg']);
      }
    },
  });
}

function login_2() {
  let ID = $("#login-ID-input").val();
  let PW = $("#login-PW-input").val();

  $.ajax({
    type: "POST", // POST 방식으로 요청하겠다.
    url: "/login_2",
    data: { ID_give: ID, PW_give: PW }, // 데이터를 주는 방법
    success: function (response) {
      // 성공하면
      if (response["result"] == "success") {
        localStorage.setItem("token", response["access_token"]);

        alert("로그인 성공!");
        // 3. 성공 시 페이지 새로고침하기
        window.location.href = "afterLogin";
      } else {
        alert(response['msg']);
      }
    },
  });
}