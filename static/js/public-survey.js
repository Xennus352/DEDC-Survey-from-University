'use strict';

(function () {
  function normalize(value) {
    return String(value || '').toLocaleLowerCase('my').trim();
  }

  function setInvalid(control, message, errorNode, wrapper) {
    if (!control) return;
    control.classList.add('is-invalid');
    control.setAttribute('aria-invalid', 'true');
    if (wrapper) wrapper.classList.add('is-invalid');
    if (errorNode) {
      errorNode.textContent = message;
      errorNode.hidden = false;
    }
  }

  function clearInvalid(control, errorNode, wrapper) {
    if (control) {
      control.classList.remove('is-invalid');
      control.removeAttribute('aria-invalid');
    }
    if (wrapper) wrapper.classList.remove('is-invalid');
    if (errorNode) {
      errorNode.textContent = '';
      errorNode.hidden = true;
    }
  }

  function initCombobox(root) {
    const input = root.querySelector('[data-combobox-input]');
    const hidden = root.querySelector('[data-combobox-value]');
    const menu = root.querySelector('[data-combobox-menu]');
    const toggle = root.querySelector('[data-combobox-toggle]');
    const empty = root.querySelector('[data-combobox-empty]');
    const error = root.querySelector('[data-combobox-error]');
    if (!input || !hidden || !menu) return null;

    const options = Array.from(menu.querySelectorAll('[role="option"]'));
    const label = root.dataset.comboboxLabel || 'တန်ဖိုး';
    let activeIndex = -1;

    function visibleOptions() {
      return options.filter(function (option) {
        return !option.hidden;
      });
    }

    function selectedOption() {
      return options.find(function (option) {
        return option.dataset.value === hidden.value;
      });
    }

    function setActive(index) {
      const visible = visibleOptions();
      options.forEach(function (option) {
        option.classList.remove('is-active');
      });
      activeIndex = index;
      const option = visible[activeIndex];
      if (!option) {
        input.removeAttribute('aria-activedescendant');
        return;
      }
      option.classList.add('is-active');
      input.setAttribute('aria-activedescendant', option.id);
      option.scrollIntoView({ block: 'nearest' });
    }

    function filter(query) {
      const needle = normalize(query);
      let count = 0;
      options.forEach(function (option) {
        const match = normalize(option.dataset.label).includes(needle);
        option.hidden = !match;
        if (match) count += 1;
      });
      if (empty) empty.hidden = count !== 0;
      setActive(count ? 0 : -1);
      return count;
    }

    function openMenu(query) {
      menu.hidden = false;
      root.classList.add('is-open');
      input.setAttribute('aria-expanded', 'true');
      filter(query);
    }

    function closeMenu() {
      menu.hidden = true;
      root.classList.remove('is-open');
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      if (empty) empty.hidden = true;
      activeIndex = -1;
    }

    function clearSelection() {
      hidden.value = '';
      options.forEach(function (option) {
        option.setAttribute('aria-selected', 'false');
      });
    }

    function clearError() {
      root.classList.remove('is-invalid');
      input.removeAttribute('aria-invalid');
      if (error) {
        error.textContent = '';
        error.hidden = true;
      }
    }

    function validate() {
      const selected = selectedOption();
      const valid =
        Boolean(selected) &&
        input.value.trim() === selected.dataset.label.trim();

      closeMenu();
      if (valid) {
        clearError();
        return true;
      }

      if (selected) clearSelection();
      const message = input.value.trim()
        ? label +
          ' စာရင်းတွင် မပါဝင်ပါ။ စာရင်းမှ ရွေးချယ်ပါ။'
        : label + ' ကို စာရင်းမှ ရွေးချယ်ပါ။';
      root.classList.add('is-invalid');
      input.setAttribute('aria-invalid', 'true');
      if (error) {
        error.textContent = message;
        error.hidden = false;
      }
      return false;
    }

    function selectOption(option) {
      hidden.value = option.dataset.value;
      input.value = option.dataset.label;
      options.forEach(function (item) {
        item.setAttribute('aria-selected', String(item === option));
      });
      clearError();
      closeMenu();
      input.focus();
    }

    function openForBrowsing() {
      const selected = selectedOption();
      openMenu(
        selected && input.value === selected.dataset.label ? '' : input.value
      );
    }

    input.addEventListener('click', function () {
      if (menu.hidden) openForBrowsing();
    });

    input.addEventListener('input', function () {
      const selected = selectedOption();
      if (selected && input.value !== selected.dataset.label) {
        clearSelection();
      }
      clearError();
      openMenu(input.value);
    });

    input.addEventListener('keydown', function (event) {
      const visible = visibleOptions();
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (menu.hidden) {
          openForBrowsing();
          return;
        }
        setActive(Math.min(activeIndex + 1, visible.length - 1));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (menu.hidden) {
          openForBrowsing();
          return;
        }
        setActive(Math.max(activeIndex - 1, 0));
      } else if (event.key === 'Home' && !menu.hidden) {
        event.preventDefault();
        setActive(0);
      } else if (event.key === 'End' && !menu.hidden) {
        event.preventDefault();
        setActive(visible.length - 1);
      } else if (event.key === 'Enter' && !menu.hidden && activeIndex >= 0) {
        event.preventDefault();
        selectOption(visible[activeIndex]);
      } else if (event.key === 'Escape' && !menu.hidden) {
        event.preventDefault();
        const selected = selectedOption();
        if (selected) input.value = selected.dataset.label;
        closeMenu();
      } else if (event.key === 'Tab') {
        closeMenu();
      }
    });

    if (toggle) {
      toggle.addEventListener('click', function () {
        if (menu.hidden) {
          openForBrowsing();
          input.focus();
        } else {
          closeMenu();
        }
      });
    }

    options.forEach(function (option) {
      option.addEventListener('click', function () {
        selectOption(option);
      });
    });

    document.addEventListener('click', function (event) {
      if (!root.contains(event.target)) closeMenu();
    });

    const selected = selectedOption();
    if (selected) {
      input.value = selected.dataset.label;
      selected.setAttribute('aria-selected', 'true');
    } else if (hidden.value) {
      clearSelection();
    }

    return {
      validate: validate,
      element: input,
    };
  }

  function initQuestion(question) {
    const details = question.querySelector('[data-question-details]');
    if (!details) return null;

    const fields = Array.from(details.querySelectorAll('input, textarea'));
    const radios = Array.from(question.querySelectorAll('input[type="radio"]'));
    const answerFieldset = question.querySelector('[data-answer-fieldset]');
    const radioError = question.querySelector('[data-radio-error]');
    const count = details.querySelector('input[type="number"]');
    const countError = question.querySelector('[data-count-error]');
    const description = details.querySelector('textarea');
    const descriptionError = question.querySelector('[data-description-error]');

    function clearQuestionErrorIfEmpty() {
      if (!question.querySelector('.uni-field-error:not([hidden])')) {
        question.classList.remove('has-client-error');
      }
    }

    function updateFields() {
      const checked = question.querySelector('input[type="radio"]:checked');
      const show = Boolean(checked && checked.value === '1');
      details.hidden = !show;
      fields.forEach(function (field) {
        field.disabled = !show;
      });
      if (!show) {
        clearInvalid(count, countError, count && count.closest('.uni-field'));
        clearInvalid(
          description,
          descriptionError,
          description && description.closest('.uni-field')
        );
        clearQuestionErrorIfEmpty();
      }
    }

    function validateCount() {
      if (!count) return '';
      if (count.validity && count.validity.badInput) {
        return 'မှန်ကန်သော အရေအတွက် ဖြည့်ပါ။';
      }
      const raw = count.value.trim();
      if (!raw) return 'အရေအတွက် ဖြည့်ပါ။';
      if (!/^\d+$/.test(raw)) {
        return 'မှန်ကန်သော အရေအတွက် ဖြည့်ပါ။';
      }
      if (Number(raw) > 2147483647) {
        return 'အရေအတွက် ပမာဏ များလွန်းနေပါသည်။';
      }
      return '';
    }

    function validateDescription() {
      if (!description) return '';
      if (!description.value.trim()) return 'အကြောင်းအရာ ဖြည့်ပါ။';
      if (description.value.length > 4000) {
        return 'အကြောင်းအရာသည် စာလုံး ၄၀၀၀ လုံးထက် မကျော်ရပါ။';
      }
      return '';
    }

    function validate() {
      let firstInvalid = null;
      const checked = question.querySelector('input[type="radio"]:checked');

      clearInvalid(answerFieldset, radioError);
      if (!checked) {
        setInvalid(
          answerFieldset,
          'ရှိ/မရှိ ကို ရွေးချယ်ပါ။',
          radioError
        );
        firstInvalid = radios[0] || null;
      }

      if (checked && checked.value === '1') {
        const countMessage = validateCount();
        if (countMessage) {
          setInvalid(
            count,
            countMessage,
            countError,
            count && count.closest('.uni-field')
          );
          if (!firstInvalid) firstInvalid = count;
        } else {
          clearInvalid(count, countError, count && count.closest('.uni-field'));
        }

        const descriptionMessage = validateDescription();
        if (descriptionMessage) {
          setInvalid(
            description,
            descriptionMessage,
            descriptionError,
            description && description.closest('.uni-field')
          );
          if (!firstInvalid) firstInvalid = description;
        } else {
          clearInvalid(
            description,
            descriptionError,
            description && description.closest('.uni-field')
          );
        }
      } else {
        clearInvalid(count, countError, count && count.closest('.uni-field'));
        clearInvalid(
          description,
          descriptionError,
          description && description.closest('.uni-field')
        );
      }

      question.classList.toggle('has-client-error', Boolean(firstInvalid));
      return firstInvalid;
    }

    radios.forEach(function (radio) {
      radio.addEventListener('change', function () {
        clearInvalid(answerFieldset, radioError);
        clearQuestionErrorIfEmpty();
        updateFields();
        if (radio.value === '1' && radio.checked && count) {
          count.focus();
        }
      });
    });

    if (count) {
      count.addEventListener('input', function () {
        clearInvalid(count, countError, count.closest('.uni-field'));
        clearQuestionErrorIfEmpty();
      });
    }

    if (description) {
      description.addEventListener('input', function () {
        clearInvalid(
          description,
          descriptionError,
          description.closest('.uni-field')
        );
        clearQuestionErrorIfEmpty();
      });
    }

    updateFields();
    return {
      validate: validate,
      updateFields: updateFields,
    };
  }

  function initProgress(form) {
    const questions = Array.from(
      form.querySelectorAll('[data-survey-question]')
    );
    const groups = Array.from(form.querySelectorAll('[data-survey-group]'));
    const navItems = Array.from(
      document.querySelectorAll('.uni-group-nav__item')
    );
    const progressCount = document.querySelector('[data-progress-count]');
    const progressBar = document.querySelector('[data-progress-bar]');
    const progressLabel = document.querySelector('[data-progress-label]');
    const submitProgress = document.querySelector('[data-submit-progress]');
    const total = questions.length;

    function isComplete(question) {
      const checked = question.querySelector('input[type="radio"]:checked');
      if (!checked) return false;
      if (checked.value === '0') return true;
      const count = question.querySelector('input[type="number"]');
      const description = question.querySelector('textarea');
      return Boolean(
        count &&
          description &&
          count.value.trim() !== '' &&
          description.value.trim() !== ''
      );
    }

    function setGroupCount(key, completed, groupTotal) {
      document.querySelectorAll('[data-group-count]').forEach(function (node) {
        if (node.dataset.groupCount === String(key)) {
          node.textContent = String(completed) + ' / ' + String(groupTotal);
        }
      });
    }

    function update() {
      let completed = 0;
      const groupTotals = new Map();

      questions.forEach(function (question) {
        const done = isComplete(question);
        question.classList.toggle('is-complete', done);
        if (done) completed += 1;

        const group = question.closest('[data-survey-group]');
        if (!group) return;
        const key = group.dataset.surveyGroup;
        const entry = groupTotals.get(key) || { done: 0, total: 0 };
        entry.total += 1;
        if (done) entry.done += 1;
        groupTotals.set(key, entry);
      });

      groups.forEach(function (group) {
        const key = group.dataset.surveyGroup;
        const entry = groupTotals.get(key) || { done: 0, total: 0 };
        setGroupCount(key, entry.done, entry.total);
      });

      document.querySelectorAll('[data-group-card]').forEach(function (card) {
        const entry = groupTotals.get(card.dataset.groupCard) || {
          done: 0,
          total: 0,
        };
        card.classList.toggle(
          'is-complete',
          entry.total > 0 && entry.done === entry.total
        );
      });

      navItems.forEach(function (item) {
        const entry = groupTotals.get(item.dataset.openGroup) || {
          done: 0,
          total: 0,
        };
        item.classList.toggle(
          'is-complete',
          entry.total > 0 && entry.done === entry.total
        );
      });

      if (progressCount) progressCount.textContent = String(completed);
      if (progressBar) {
        progressBar.style.width =
          (total ? (completed / total) * 100 : 0) + '%';
      }
      if (submitProgress) {
        submitProgress.textContent =
          String(completed) + ' / ' + String(total) + ' ဖြေဆိုပြီး';
      }
      if (progressLabel) {
        if (completed === 0) {
          progressLabel.textContent = 'မေးခွန်းများကို စတင်ဖြေဆိုပါ။';
        } else if (completed === total) {
          progressLabel.textContent =
            'မေးခွန်းအားလုံး ဖြေဆိုပြီးပါပြီ။ အောက်တွင် ပေးပို့ပါ။';
        } else {
          progressLabel.textContent =
            String(total - completed) + ' ခု ကျန်ရှိပါသည်။';
        }
      }
    }

    form.addEventListener('change', update);
    form.addEventListener('input', update);
    update();
  }

  function initGroupWizard(form) {
    const groups = Array.from(form.querySelectorAll('[data-survey-group]'));
    if (!groups.length) return null;

    const overview = form.querySelector('[data-overview]');
    const stage = form.querySelector('[data-answer-stage]');
    const stageTitle = form.querySelector('[data-stage-title]');
    const stageKicker = form.querySelector('[data-stage-kicker]');
    const overviewTitle = form.querySelector('[data-overview-title]');
    const openButtons = Array.from(document.querySelectorAll('[data-open-group]'));
    const closeButton = form.querySelector('[data-close-stage]');
    const prevButtons = Array.from(form.querySelectorAll('[data-prev-group]'));
    const nextButtons = Array.from(form.querySelectorAll('[data-next-group]'));
    const navItems = Array.from(document.querySelectorAll('.uni-group-nav__item'));
    const groupIndex = new Map();
    let currentIndex = -1;

    groups.forEach(function (group, index) {
      groupIndex.set(String(group.dataset.surveyGroup), index);
    });

    function currentKey() {
      return currentIndex >= 0 && groups[currentIndex]
        ? String(groups[currentIndex].dataset.surveyGroup)
        : '';
    }

    function syncNavigation() {
      const activeKey = currentKey();
      navItems.forEach(function (item) {
        item.classList.toggle(
          'is-current',
          String(item.dataset.openGroup) === activeKey
        );
      });
      prevButtons.forEach(function (button) {
        button.disabled = currentIndex <= 0;
      });
      nextButtons.forEach(function (button) {
        button.disabled =
          currentIndex < 0 || currentIndex >= groups.length - 1;
      });
    }

    function showOverview(shouldFocus) {
      currentIndex = -1;
      groups.forEach(function (group) {
        group.hidden = true;
      });
      if (stage) stage.hidden = true;
      if (overview) overview.hidden = false;
      if (stageTitle) stageTitle.textContent = '';
      if (stageKicker) stageKicker.textContent = '';
      syncNavigation();

      if (shouldFocus && overviewTitle) {
        const reduceMotion = window.matchMedia(
          '(prefers-reduced-motion: reduce)'
        ).matches;
        window.requestAnimationFrame(function () {
          overviewTitle.focus({ preventScroll: true });
          overviewTitle.scrollIntoView({
            behavior: reduceMotion ? 'auto' : 'smooth',
            block: 'start',
          });
        });
      }
    }

    function openIndex(index, options) {
      if (index < 0 || index >= groups.length) return;
      const settings = options || {};
      const group = groups[index];
      currentIndex = index;

      groups.forEach(function (item) {
        item.hidden = item !== group;
      });
      if (overview) overview.hidden = true;
      if (stage) stage.hidden = false;
      if (stageTitle) {
        stageTitle.textContent = group.dataset.groupTitle || '';
      }
      if (stageKicker) {
        stageKicker.textContent =
          'မေးခွန်းအုပ်စု ' + String(index + 1) + ' / ' + String(groups.length);
      }
      syncNavigation();

      const focusTarget = settings.focus || null;
      if (!focusTarget && settings.focusTitle === false) return;

      const reduceMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      ).matches;
      window.requestAnimationFrame(function () {
        if (focusTarget) {
          focusTarget.focus({ preventScroll: true });
          focusTarget.scrollIntoView({
            behavior: reduceMotion ? 'auto' : 'smooth',
            block: 'center',
          });
          return;
        }
        if (stageTitle) {
          stageTitle.focus({ preventScroll: true });
          if (stage) {
            stage.scrollIntoView({
              behavior: reduceMotion ? 'auto' : 'smooth',
              block: 'start',
            });
          }
        }
      });
    }

    function openKey(key, options) {
      const index = groupIndex.get(String(key));
      if (index === undefined) return;
      openIndex(index, options);
    }

    openButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        openKey(button.dataset.openGroup);
      });
    });

    if (closeButton) {
      closeButton.addEventListener('click', function () {
        showOverview(true);
      });
    }

    prevButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        if (currentIndex > 0) openIndex(currentIndex - 1);
      });
    });

    nextButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        if (currentIndex >= 0 && currentIndex < groups.length - 1) {
          openIndex(currentIndex + 1);
        }
      });
    });

    function groupForQuestion(question) {
      const group = question.closest('[data-survey-group]');
      return group ? String(group.dataset.surveyGroup) : '';
    }

    const firstServerError = form.querySelector(
      '[data-survey-question].uni-question--error'
    );
    const identityInvalid = document.querySelector(
      '[data-combobox].is-invalid'
    );
    if (!identityInvalid && firstServerError) {
      const key = groupForQuestion(firstServerError);
      if (key) openKey(key, { focusTitle: false });
    } else if (!identityInvalid && window.location.hash) {
      const targetId = window.location.hash.slice(1);
      const target = groups.find(function (group) {
        return group.id === targetId;
      });
      if (target) {
        openKey(target.dataset.surveyGroup, { focusTitle: false });
      }
    }

    return {
      openKey: openKey,
      showOverview: showOverview,
      groupForQuestion: groupForQuestion,
    };
  }

  function init() {
    const comboboxes = Array.from(
      document.querySelectorAll('[data-combobox]')
    )
      .map(initCombobox)
      .filter(Boolean);

    const form = document.querySelector('[data-public-survey]');
    if (!form) return;

    const questions = Array.from(
      form.querySelectorAll('[data-survey-question]')
    )
      .map(initQuestion)
      .filter(Boolean);

    const wizard = initGroupWizard(form);
    initProgress(form);

    form.addEventListener('submit', function (event) {
      let firstInvalid = null;
      let firstInvalidQuestion = null;

      comboboxes.forEach(function (combobox) {
        if (!combobox.validate() && !firstInvalid) {
          firstInvalid = combobox.element;
        }
      });

      questions.forEach(function (question) {
        const invalid = question.validate();
        if (invalid && !firstInvalid) {
          firstInvalid = invalid;
          firstInvalidQuestion = question;
        }
      });

      if (!firstInvalid) return;

      event.preventDefault();

      if (firstInvalidQuestion && wizard) {
        const key = wizard.groupForQuestion(firstInvalidQuestion);
        if (key) {
          wizard.openKey(key, { focus: firstInvalid });
          return;
        }
      }

      if (wizard) wizard.showOverview();

      const reduceMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      ).matches;
      window.requestAnimationFrame(function () {
        firstInvalid.focus({ preventScroll: true });
        firstInvalid.scrollIntoView({
          behavior: reduceMotion ? 'auto' : 'smooth',
          block: 'center',
        });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
