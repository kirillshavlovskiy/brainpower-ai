
    let editor;
    let editor_AI;
    let input_AI;
    let output_form;
    let previousLine;
    let formData = new FormData();
    let AI_formData = new FormData();
    let current_task;

var myElement = document.getElementById('wrapper-left');
var startIDEUrl = myElement.getAttribute('data-start-interpreter');


    // Display the contents of the FormData object
    function logFormData(formData) {
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
    }






    function handleExecutionClick(taskId, event) {
                if (event) {
                    event.preventDefault(); // Prevent form submission
                }
                const taskTextarea = document.getElementById('task-' + taskId);
                const code_example = taskTextarea.value;
                editor.setValue(code_example);
                const taskData = new FormData();
                taskData.append('task_id', taskId);
                taskData.append('code', code_example);
                output_form.setValue('')

                fetch('/courses/thread_start/', {
                    method: 'POST',
                    body: taskData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => {
                        Prism.highlightAll();
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                        .then(data => {
                            if (data.task_description) {
                                console.log('new thread is initiated')
                                AI_formData = new FormData();
                                AI_formData.append('thread_id', data.thread_id);
                                AI_formData.append('task_id', taskId);
                                AI_formData.append('assistant_id', data.assistant_id);
                                AI_formData.append('code', code_example);
                                AI_formData.append('output', '');
                                // Assuming 'editor_AI' is another instance of CodeMirror
                                editor_AI.setValue('###___Thread ID:___' + data.thread_id + '\n\n###___Task:___' + data.task_description +'\n\n###___Coding Assistant (auto):___ \n\nHello, my name is Mr.Code. I am your teaching assistant today! Nice to meet you and lets start our practice. I gave you some code examples to start practicing.' + data.ai_response + '\n\nNow you can check the result of sample code execution after pressing the Submit button. \n\nYou can ask me further any questions should you have them about this lesson!');
                                // Add the event listener to capture output form changes
                                thread = editor_AI.getValue();
                                const save_form = new FormData();
                                save_form.append('thread', thread)
                                save_form.append('task_id', taskId);
                                save_form.append('code', code_example);
                                 fetch('/courses/thread_save/', {
                                    method: 'POST',
                                    body: save_form,
                                    headers: {
                                        'X-CSRFToken': getCookie('csrftoken')
                                    }
                                })
                                .then(response => {
                                    if (!response.ok) {
                                        throw new Error('Network response was not ok');
                                    }
                                        return response.json();
                                    })
                                        .then(data => {
                                            if (data.system_message) {
                                           editor_AI.setValue(thread + '\n\nSaved\n\n')
                                            }


                                });

                            } else {  if (data.messages) {
                                AI_formData = new FormData();
                                AI_formData.append('thread_id', data.thread_id);
                                AI_formData.append('task_id', taskId);
                                AI_formData.append('assistant_id', data.assistant_id);
                                AI_formData.append('code', code_example);
                                AI_formData.append('output', '');

                                console.log('thread is retrieved')
                                editor_AI.setValue(data.messages)
                                        } else {
                                let thread = editor_AI.getValue();
                                editor_AI.setValue('\n\n' + thread + '\n\n###___Coding Assistant:___\n\nAssistant is not responding, try again in a moment...');
                                } }
                               current_task = taskId;
                               AI_formData.set('task_id', current_task);
                            });

            }

    //reserve function to retrieve all the messages (system and user) in the thread
    function handleRetrievalClick(taskId, event) {
                if (event) {
                    event.preventDefault(); // Prevent form submission
                }
                const taskTextarea = document.getElementById('task-' + taskId);
                const code_example = taskTextarea.value
                editor.setValue(code_example);
                const taskData = new FormData();


                fetch('/courses/thread_retrieve/', {
                    method: 'POST',
                    body: AI_formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
            .then(response => {

                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                    .then(data => {
                        updateCodeMirror(data.messages);
                    });

            }

    // Function to update CodeMirror with messages
    function updateCodeMirror(messages) {
        // Check if messages array exists
        if (messages && messages.length > 0) {
            // Assuming 'editor' is your CodeMirror instance
            messages.forEach(message => {
                // Append each message to the CodeMirror instance
                // You can use setValue() or replaceRange() based on your requirements
                editor.replaceRange(message.text + '\n', CodeMirror.Pos(editor.lastLine()));
            });
        } else {
            console.log('No messages found.'); // Log a message if no messages are found
        }
    }



    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('code-form');
        const form_ai = document.getElementById('code-form-ai');
        const form_input_ai = document.getElementById('code-input-ai');
        AI_formData = new FormData(form_input_ai);
        output_form = CodeMirror.fromTextArea(document.getElementById('code_output'), {
            lineNumbers: false,
            mode: 'text',
            theme: 'ayu-mirage',
            readonly: true,

        });


        editor = CodeMirror.fromTextArea(form.querySelector('textarea'), {
            lineNumbers: true,
            mode: 'python',
            theme: 'ayu-mirage',
            gutters: ['CodeMirror-lint-markers'],
            lint: true,
            spellcheck:true
        });



        editor_AI = CodeMirror.fromTextArea(form_ai.querySelector('textarea'), {
              mode: "markdown",
              theme: "ayu-mirage",
              lineNumbers: false,
              lineWrapping: true

            });

        input_AI = CodeMirror.fromTextArea(form_input_ai.querySelector('textarea'), {
                    lineNumbers: false,
                    mode: 'text',
                    theme: 'tomorrow-night-eighties',
        });


        editor.setSize(null, "500px"); // Set the height to 400px
        editor_AI.setSize(null, "500px"); // Set the height to 400px
        input_AI.setSize(null, "200px"); // Set the height to 400px
        output_form.setSize(null, "200px"); // Set the height to 400px

        const editorElement = editor.getWrapperElement();
        const AI_editorElement = editor_AI.getWrapperElement();
        const AI_inputElement = input_AI.getWrapperElement();

        AI_editorElement.classList.add('customClass');
        editor_AI.setOption('readOnly', true);

        form_input_ai.addEventListener('submit', handleAIFormSubmission)

        // Define the event listener for form submission
        form.addEventListener('submit', handleFormSubmission);

        // Define the event listener for output_form content changes
        function handleOutputFormChange(instance, changeObj) {
                //handleResponseAI(instance.getValue());
                }

        // Define the event listener for output_form content changes
        editor.on('change', function(instance, changeObj) {
        cleanHighlight(instance.getValue());
        });



        // Function to clear all highlights from editor
        function cleanHighlight() {
        // Check if previousLine is not null before removing the class
            if (previousLine) {
                editor.removeLineClass(previousLine, 'background', 'highlighted-line');
                editor.removeLineClass(previousLine, 'background', 'error-highlighted-line');
                editor.removeLineClass(editor.lineCount()-1, 'background', 'highlighted-line-finish');
                previousLine = null;
            } else {
                editor.removeLineClass(editor.lineCount()-1, 'background', 'highlighted-line-finish');
            }
        }

        // Function to handle form submission to AI
        function handleResponseAI() {
            console.log('handleResponseAI triggered')
            const output = output_form.getValue().trim();
            const code = editor.getValue().trim();

            AI_formData.set('output', output);
            AI_formData.set('code', code);

            form_input_ai.dataset.code = code
            form_input_ai.dataset.output = output

            logFormData(AI_formData);
            fetch('/courses/process_code/', {
                method: 'POST',
                body: AI_formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
             .then(response => {


                if (!response.ok) {
                    throw new Error('Network response was not ok');
                    thread = editor_AI.getValue();
                    editor_AI.setValue('\n\n###___Thread ID:___' + data.thread_id + '\n\nSystem: Assistant is not responding, please try in a moment.\nInput your question below again:\n');
                }
                return response.json();
            })
           .then(data => {
                if (data.ai_response) {

                        // Call the function to log the contents of formData
                        logFormData(AI_formData);
                        // Set the content and mark specific lines as editable
                        const thread = editor_AI.getValue()
                        editor_AI.setValue(thread + '\n\n###___Thread ID:___' + data.thread_id + '\n\n###___Coding Assistant (auto):___' + data.ai_response);
                if (AI_formData.task_id) {
                const save_form = new FormData();
                save_form.append('thread', thread)
                save_form.append('task_id', taskId);
                save_form.append('code', code_example);

                 fetch('/courses/thread_save/', {
                    method: 'POST',
                    body: AI_formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                        return response.json();
                    })
                        .then(data => {
                            if (data.system_message) {
                           editor_AI.setValue(thread + '\n\nSaved\n\n')
                            }


                });
                }
                }

                })
                .catch(error => {
                    console.error('Error:', error);
                    output_form.setValue('An error occurred while processing your request');
                });
        }

function handleCodeCompletion(event) {
    if (event) {
                    event.preventDefault(); // Prevent form submission
                }

    const formData = new FormData(form);

    // Check if code is empty
    if (editor.getValue().trim() === '') {
        console.error('Code is empty');
        output_form.setValue('Please type your code before pressing "Submit" button.');
        editorElement.classList.remove('customClass');
        return;
    } else {
        const code = editor.getValue().trim();
        formData.set('code', code);
        formData.append('language', "python");
        console.log(formData.entries());
    }
    editorElement.classList.add('customClass');
    editor.setOption('readOnly', true);
    // Add the event listener to capture output form changes
    console.log('Code execution started');
    logFormData(AI_formData);
    if (AI_formData.task_id !== null) {
    console.log('current task: ', AI_formData.task_id);
    output_form.on('change', handleOutputFormChange);
    }

     //editorElement.classList.add('customClass');
     editor.setOption('readOnly', true);
    // Add the event listener to capture output form changes
    logFormData(formData);
    fetch('/courses/start_chat_with_agent/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => {
            editor.setOption('readOnly', false);
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
               if (!data.completion) {

                // Append AI message to the thread
                logFormData(AI_formData);
                let thread = editor_AI.getValue();
                editor_AI.setValue(thread + '\n\n###___Coding Assistant:___\n\n' + data.corrected_code);
                // Delete message from input form

            } else {
                let thread = editor_AI.getValue();
                editor_AI.setValue(thread + '\n\n###___Coding Assistant:___\n\nYour code is correct and should return following execution output: \n'+ data.output);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            output_form.setValue('An error occurred while processing your request');
        });
}


        // Function to handle chat with AI
        function handleAIFormSubmission(event) {
        event.preventDefault();
        console.log("message processing started")

        AI_inputElement.classList.add('customClass');
        input_AI.setOption('readOnly', true);

        message = input_AI.getValue();
        AI_formData.append('input_message', message);
        fetch('/courses/agent-chat-start/', {
            method: 'POST',
            body: AI_formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            AI_inputElement.classList.remove('customClass');
            input_AI.setOption('readOnly', false);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {

            if (data.completion) {

                // Append AI message to the thread
                logFormData(AI_formData);

                editor_AI.setValue('###___User:___\n\n' + message + '\n\n###___Coding Agent:___\n\nCompletion status:\n' + data.completion + '\nresponse:\n' + data.response);
                editor.setValue(data.code, data.streamlit_code)
                // Delete message from input form
                input_AI.setValue('');
            } else {
                let thread = editor_AI.getValue();
                editor_AI.setValue('###___User:___\n\n' + message + '\n\n###___Coding Agent:___\n\nAssistant is not responding, try again in a moment...');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            output_form.setValue('An error occurred while processing your request:(((');
        });


        }

        // Function to handle form submission to server subprocess (interpreter)
        function handleFormSubmission(event) {
            event.preventDefault();

            formData = new FormData(form);

            let symbolsProcessed = 0;
            let inputsProcessed = 0

            // Check if code is empty
            if (editor.getValue().trim() === '') {
                console.error('Code is empty');
                output_form.setValue('Please type your code before pressing "Submit" button.');
                editorElement.classList.remove('customClass');
                return;
            } else {
                const code = editor.getValue().trim();
                formData.set('code', code);
            }
            editorElement.classList.add('customClass');
            editor.setOption('readOnly', true);
            output_form.setValue('');
            // Add the event listener to capture output form changes
            console.log('Code execution started');
             logFormData(AI_formData);
            if (AI_formData.task_id !== null) {
            console.log('current task: ', AI_formData.task_id);
            output_form.on('change', handleOutputFormChange);
            }

            // Initialize inputsProcessed to 0 if not already set
            form.dataset.inputsProcessed = form.dataset.inputsProcessed ? parseInt(form.dataset.inputsProcessed) : 0;
            // Initialize symbolsProcessed to '' if not already set
            form.dataset.symbolsProcessed = form.dataset.symbolsProcessed ? form.dataset.symbolsProcessed : '';

            fetch(startIDEUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => {
            //editorElement.classList.remove('customClass');


                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {


                if (data.input_requested) {
                    console.log('Control - move to Input!');
                    const prompt_line = parseInt(data.prompt_message);
                    output_form.setValue(data.output + '\n');
                    form.removeEventListener('submit', handleFormSubmission);

                    form.addEventListener('submit', handleInputSubmission);
                    //Update symbols processed stats
                    form.dataset.symbolsProcessed = data.output;

                    if (prompt_line) {
                        editor.addLineClass(prompt_line, 'background', 'highlighted-line');
                        previousLine = prompt_line;

                    }
                } else {
                editor.setOption('readOnly', false);
                const prompt_line = parseInt(data.prompt_message);
                    if (data.completed) {
                                if (data.image) {  // Checking if there is a base64 encoded image in the response
                                console.log("image-flow")
                                console.log(data)
                                const plotImage = document.getElementById('plotImage');
                                // Constructing and setting the src attribute to a data URL with the base64 encoded image
                                plotImage.innerHTML = '<img src="data:image/png;base64,' + data.image + '" alt="Plot Image">';
                                }
                        console.log('Code Execution Finished Successfully on line',editor.lineCount());
                        output_form.setValue(data.output + '\nScript execution successfully completed on line ' + editor.lineCount());
                        editor.addLineClass(editor.lineCount()-1, 'background', 'highlighted-line-finish');
                        previousLine = editor.lineCount()-1;
                    } else {
                        console.log('Code Execution Failed on the line', prompt_line,'with message',data.message);
                        output_form.setValue(data.output + '\nCode Execution Failed with message' + data.message);
                        editor.addLineClass(prompt_line, 'background', 'error-highlighted-line');
                        previousLine = prompt_line;
                    }
                    // Disable the event listener
                    output_form.off('change', handleOutputFormChange);

                formData.set('code', "");
                    fetch(startIDEUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                    });
                }
            }).catch(error => {
            console.error('Error:', error);
            output_form.setValue('An error occurred while processing your request');
        });


        }

        // Function to handle input submission
        function handleInputSubmission(event) {
            event.preventDefault();

            // Get the value of the last line in the output form
            const outputLines = output_form.getValue().split('\n');
            const lastLine = outputLines[outputLines.length - 1];

            // Now you can use the content of the last line as user input
            const userInput = lastLine.trim();
            const userInputList = []

            // Add it to array
            userInputList.push(userInput);

            // Process the last line as needed
            console.log('userInputList', userInputList);

            // Proceed with further processing, such as sending the user input to the server
            formData.append('input_value', userInput);
            form.dataset.input_value = userInputList

            const currentInputsProcessed = parseInt(form.dataset.inputsProcessed) || 0;  // Parse as integer or default to 0 if NaN
            form.dataset.inputsProcessed = currentInputsProcessed + 1;
            formData.append('inputs_processed', form.dataset.inputsProcessed);
            formData.append('symbols_processed', form.dataset.symbolsProcessed);

            fetch(startIDEUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => {
                // Log the raw response content to the console
                console.log('Input response:', response);
                console.log('Content-Type:', response.headers.get('Content-Type'));
                editor.setOption('readOnly', true);
                editor_AI.setOption('readOnly', true);
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {

                if (data.input_requested) {
                    const prompt_line = parseInt(data.prompt_message);
                    const currentCode = output_form.getValue().trim();
                    const updatedCode = currentCode + '\n' + data.output + '\n';  // Append output on a new line
                    output_form.setValue(updatedCode);
                    //Update symbols processed stats
                    form.dataset.symbolsProcessed = form.dataset.symbolsProcessed + data.output;
                    console.log('Input requested at line: ', prompt_line);
                    if (previousLine) {
                        editor.removeLineClass(previousLine, 'background', 'highlighted-line');
                        editor.addLineClass(prompt_line, 'background', 'highlighted-line');
                        previousLine = prompt_line;
                        // Reset cursor position to the end of the last newly added line
                        //const cursorPos = { line: output_form.lineCount(), ch: output_form.getLine(output_form.lineCount()).length };
                        //output_form.setCursor(cursorPos);

                    }
                } else {                                    //no input requested
                    if (data.completed) {                   //execution completed
                    // Remove the event listener for input submission
                    form.removeEventListener('submit', handleInputSubmission);
                    // Add the event listener for form submission
                    form.addEventListener('submit', handleFormSubmission);
                    //Code execution complete, update output form with the code execution result
                        console.log('Code Execution Finished Successfully!');
                        const currentCode = output_form.getValue().trim();  // Get current code in output_form
                        const updatedCode = currentCode + '\n' + data.output + '\n' + 'Script Execution Completed. No error detected :)';  // Append output on a new line
                        output_form.setValue(updatedCode);
                        if (previousLine) {
                            console.log('Output_Form cleared_1');
                            editor.removeLineClass(previousLine, 'background', 'highlighted-line');
                            console.log('Output_Form cleared, line ', previousLine);
                            console.log(editor.lineCount());
                            editor.addLineClass(editor.lineCount(), 'background', 'highlighted-line-finish');
                            previousLine = null
                        } else {
                            console.log('Output_Form cleared_2');
                            console.log(editor.lineCount());
                            editor.addLineClass(editor.lineCount(), 'background', 'highlighted-line-finish');
                        }
                    } else {                                                // incomplete with error
                        console.log('Code Execution Stopped!');
                        const currentCode = output_form.getValue().trim();  // Get current code in output_form
                        const updatedCode = currentCode + '\n' + data.output + '\n' + 'Script Execution Completed. No error detected :)';  // Append output on a new line
                        output_form.setValue(updatedCode);
                        if (previousLine) {
                            console.log('Output_Form cleared_3');
                            editor.removeLineClass(previousLine, 'background', 'highlighted-line');
                            console.log('Output_Form cleared, line ', previousLine);
                            console.log(editor.lineCount());
                            editor.addLineClass(editor.lineCount(), 'background', 'error-highlighted-line');
                        } else {
                            console.log('Output_Form cleared_4');
                            console.log(editor.lineCount());
                            editor.addLineClass(editor.lineCount(), 'background', 'error-highlighted-line');
                        }
                    }
                    const AI_editorElement = editor_AI.getWrapperElement()
                    previousLine = null
                    editor.setOption('readOnly', false);

                    formData.set('code', "");
                    fetch(startIDEUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                    });
                    }
            })
            .catch(error => {
                console.error('Error:', error);
                output_form.setValue('an error occurred while processing your request');
            });
        }






    });