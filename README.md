# backend
AI 팀플 백엔드

# 🚀 개발 규칙 및 Git 컨벤션

원활한 협업과 효율적인 프로젝트 관리를 위해 다음 개발 규칙 및 Git 컨벤션을 준수합니다.

## 🌳 Branch 전략

프로젝트는 **Gitflow**를 기반으로 한 간소화된 브랜치 전략을 사용합니다.

* **`main`**: **운영 환경**에 배포되는 브랜치입니다. 오직 `develop` 브랜치 또는 `hotfix` 브랜치에서 병합(Merge)됩니다. **직접적인 Push 및 Commit은 절대 금지합니다.**
* **`develop`**: **다음 릴리즈 버전**을 개발하는 메인 브랜치입니다. 모든 기능 개발(`feature`) 및 버그 수정(`fix`) 브랜치는 `develop` 브랜치를 기준으로 생성하며, 개발 완료 후 `develop` 브랜치로 Pull Request를 통해 병합됩니다. **직접적인 Push는 지양하고 Pull Request를 사용합니다.**
* **`feature/<feature-name>`**: 새로운 기능 개발 시 사용하는 브랜치입니다.
    * `develop` 브랜치에서 분기합니다.
    * 기능 이름은 명확하고 간결하게 영어로 작성합니다. (예: `feature/watchlist-add`, `feature/ai-report-display`)
    * 개발 완료 후 `develop` 브랜치로 Pull Request(PR)를 생성합니다.
* **`fix/<issue-or-description>`**: 버그 수정 시 사용하는 브랜치입니다.
    * `develop` 브랜치에서 분기하는 것을 원칙으로 합니다. (단, 긴급한 운영 환경 버그는 `hotfix` 사용)
    * 이슈 번호나 간략한 설명으로 이름을 작성합니다. (예: `fix/login-error`, `fix/#123-style-bug`)
    * 수정 완료 후 `develop` 브랜치로 Pull Request(PR)를 생성합니다.
* **`refactor/<description>`**: 코드 리팩토링 시 사용하는 브랜치입니다.
    * 기능 변경 없이 코드 구조 개선 시 사용합니다. (예: `refactor/state-management`)
    * 완료 후 `develop` 브랜치로 Pull Request(PR)를 생성합니다.
* **(선택) `hotfix/<issue-or-description>`**: **긴급한 운영 환경 버그 수정** 시 사용합니다.
    * `main` 브랜치에서 분기합니다.
    * 수정 완료 후 **`main` 브랜치와 `develop` 브랜치 모두에게** PR을 생성하여 병합해야 합니다.

## ✨ Commit 메시지 규칙

Commit 메시지는 팀원들이 변경 사항을 쉽게 이해하고 추적할 수 있도록 **Conventional Commits** 양식을 따릅니다.

**형식:**
  * **`<type>`**: Commit 유형을 나타냅니다. (필수)
      * `feat`: 새로운 기능 추가
      * `fix`: 버그 수정
      * `refactor`: 코드 리팩토링 (기능 변경 없음)
      * `style`: 코드 스타일 변경 (포맷팅, 세미콜론 등. 기능 변경 없음)
      * `docs`: 문서 수정 (README 등)
      * `test`: 테스트 코드 추가/수정
      * `chore`: 빌드 관련, 패키지 매니저 설정 변경 등 (소스 코드 변경 없음)
      * `build`: 빌드 시스템 또는 외부 종속성에 영향을 미치는 변경
      * `ci`: CI 구성 파일 및 스크립트 변경

## ⬆️ Push 규칙

  * 자신의 로컬 `feature`, `fix`, `refactor` 브랜치 작업 내용은 **수시로** 원격 저장소(origin)에 Push하여 백업하고 팀원들과 진행 상황을 공유합니다.
    ```bash
    git push origin feature/your-feature-name
    ```
  * **`main`, `develop` 브랜치에는 절대 직접 Push하지 않습니다.** (필요시 브랜치 보호 규칙 설정)
  * `--force` 또는 `--force-with-lease` 옵션은 **반드시 필요한 경우에만 자신의 로컬 브랜치에 사용**하며, 사용 전 팀원과 충분히 상의합니다. 공유 브랜치(`main`, `develop`)에는 절대 사용하지 않습니다.

## ➡️ Pull Request (PR) 규칙

  * `feature`, `fix`, `refactor` 브랜치의 작업이 완료되면 `develop` 브랜치를 대상으로 Pull Request를 생성합니다. (`hotfix`는 `main`과 `develop` 모두 대상)
  * **PR 제목**: Commit 메시지 규칙과 유사하게, 변경 내용을 명확히 나타내는 제목을 작성합니다. (예: `feat(watchlist): 관심종목 삭제 기능 추가`)
  * **PR 내용 (Description)**:
      * **변경 사항 요약 (What & Why):** 어떤 작업을 왜 했는지 간략히 설명합니다.
      * **관련 이슈:** 관련된 이슈가 있다면 `Closes #이슈번호` 형식으로 링크합니다.
      * **테스트 방법:** 리뷰어가 어떻게 변경 사항을 테스트할 수 있는지 안내합니다. (필요시)
      * **스크린샷/GIF:** UI 변경 사항이 있는 경우, 변경 전/후 스크린샷이나 작동 GIF를 첨부하면 리뷰에 큰 도움이 됩니다.
  * **리뷰어 지정**: 최소 1명 이상의 팀원을 리뷰어로 지정합니다.
  * **충분한 리뷰**: 리뷰어는 코드 품질, 버그 가능성, 컨벤션 준수 여부 등을 확인하고 의견을 남깁니다.
  * **승인 및 병합**: 최소 1명 이상의 승인(Approve)을 받은 후 PR 작성자가 병합(Merge)하는 것을 원칙으로 합니다. 병합 후에는 작업 브랜치를 삭제합니다. (GitHub 설정에서 자동 삭제 옵션 활성화 권장)
      * 병합 방식은 프로젝트 상황에 맞게 선택합니다. (Merge commit, Squash and merge, Rebase and merge)