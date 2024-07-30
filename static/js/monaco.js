 var lang = document.getElementById('lang');
    var loadedThemes = null;
    var loadedThemesData = {};
    var count = 0;

    function loadTheme(theme) {
      var path = '../static/data/themes/' + loadedThemes[theme] + '.json';
      return fetch(path)
        .then(r => r.json())
        .then(data => {
          loadedThemesData[theme] = data;
          if (window.monaco) {
            monaco.editor.defineTheme(theme, data);
          }
          return data;
        });
    }

    function setEditorValue(jsn) {
      if (!window.editor) {
        return;
      }

      window.editor.setValue('const themeData = ' + JSON.stringify(jsn, null, 2));
    }

    function addFileListener() {
      var fileNode = document.getElementById('file');

      if (!window.FileReader) {
        fileNode.disabled = true;
      }

      fileNode.addEventListener('change', function(ev) {
        var file = ev.target.files[0];
        var reader = new FileReader();
        reader.onload = function(ev) {
          var themeSlug = 'localtheme-' + count;
          count++;
          loadedThemes[themeSlug] = MonacoThemes.parseTmTheme(ev.target.result);

          monaco.editor.defineTheme(themeSlug, loadedThemes[themeSlug]);
          monaco.editor.setTheme(themeSlug);
          setEditorValue(loadedThemes[themeSlug]);
        };
        reader.readAsText(file);
      });
    }

    lang.addEventListener('change', function(ev) {
      var val = ev.target.value;
      if (val === 'vs' || val === 'vs-dark' || val === 'hc-black') {
        monaco.editor.setTheme(val);
        return;
      }

      if (loadedThemesData[val]) {
        monaco.editor.setTheme(val);
        setEditorValue(loadedThemesData[val]);
      } else {
        loadTheme(val).then((data) => {
          monaco.editor.setTheme(val);
          setEditorValue(data);
        });
      }
    });

    function loadThemeList() {
        return fetch('../static/data/themes/themelist.json')
            .then(r => r.json())
            .then(data => {
                loadedThemes = data;
                var themes = Object.keys(data);
                themes.forEach(theme => {
                    var opt = document.createElement('option');
                    opt.value = theme;
                    opt.text = data[theme];
                    lang.add(opt);
                });
            });
    }

    // Call the loadThemeList function
    loadThemeList();

    require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.14.2/min/vs' }});
    window.MonacoEnvironment = {
      getWorkerUrl: function(workerId, label) {
        return `data:text/javascript;charset=utf-8,${encodeURIComponent(`
          self.MonacoEnvironment = {
            baseUrl: 'https://unpkg.com/monaco-editor@0.14.2/min'
          };
          importScripts('https://unpkg.com/monaco-editor@0.14.2/min/vs/base/worker/workerMain.js');`
        )}`;
      }
    };
    require(['vs/editor/editor.main'], function() {
      var editor = monaco.editor.create(document.getElementById('editor'), {
        value: [
          '{',
          '  "value": "Select a locally available tmtheme file or choose from the many pregenrated themes"',
          '}'
        ].join('\n'),
        language: 'python',
        fontSize: 16,
        fontFamily: 'monospace',
        minimap: {
          enabled: true,
        },
        scrollBeyondLastLine: false,
      });
      editor.focus();
      window.editor = editor;
      addFileListener();
    });

    monaco.languages.registerInlayHintsProvider("python", {
	provideInlayHints(model, range, token) {
		return {
			hints: [
				{
					kind: monaco.languages.InlayHintKind.Type,
					position: { column: 13, lineNumber: 4 },
					label: `: Number`,
				},
				{
					kind: monaco.languages.InlayHintKind.Type,
					position: { column: 13, lineNumber: 2 },
					label: `: Number`,
				},
				{
					kind: monaco.languages.InlayHintKind.Type,
					position: { column: 16, lineNumber: 2 },
					label: `: Number`,
					whitespaceBefore: true, // see difference between a and b parameter
				},
				{
					kind: monaco.languages.InlayHintKind.Parameter,
					position: { column: 18, lineNumber: 4 },
					label: `a:`,
				},
				{
					kind: monaco.languages.InlayHintKind.Parameter,
					position: { column: 21, lineNumber: 4 },
					label: `b:`,
					whitespaceAfter: true, // similar to whitespaceBefore
				},
			],
			dispose: () => {},
		};
	},
});
