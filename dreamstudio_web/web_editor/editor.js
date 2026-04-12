let htmlEditor = null;
let cssEditor = null;
let jsEditor = null;
let editorsInitialized = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, configuring require");
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});
});

function initEditor(lang) {
    console.log("Loading Monaco editor for language:", lang);
    require(['vs/editor/editor.main'], function () {
        console.log("Monaco editor main loaded for language:", lang);
        let editor;
        let container;
        let initialValue;
        
        switch(lang) {
            case 'html':
                container = document.getElementById('html-editor');
                initialValue = '<!-- HTML CODE EDITOR -->';
                break;
            case 'css':
                container = document.getElementById('css-editor');
                initialValue = '/* CSS CODE EDITOR */';
                break;
            case 'js':
                container = document.getElementById('js-editor');
                initialValue = '// JAVASCRIPT CODE EDITOR\nconsole.log("Hello");';
                break;
            default:
                return;
        }
        
        if (!container) {
            console.error("Container not found for language:", lang);
            return;
        }
        
        editor = monaco.editor.create(container, {
            value: initialValue,
            language: lang,
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 16,
            tabSize: 2,
            lineNumbers: 'on',
            minimap: { enabled: false }
        });
        
        switch(lang) {
            case 'html':
                htmlEditor = editor;
                break;
            case 'css':
                cssEditor = editor;
                break;
            case 'js':
                jsEditor = editor;
                break;
        }
        
        console.log(`Editor created for ${lang}:`, editor ? "success" : "failed");
        setTimeout(() => editor.focus(), 100);
    }).catch(err => {
        console.error("Failed to load Monaco editor for language:", lang, err);
    });
}

function getEditorValue(lang) {
    switch(lang) {
        case 'html':
            return htmlEditor ? htmlEditor.getValue() : '';
        case 'css':
            return cssEditor ? cssEditor.getValue() : '';
        case 'js':
            return jsEditor ? jsEditor.getValue() : '';
        default:
            return '';
    }
}

function setEditorValue(lang, value) {
    switch(lang) {
        case 'html':
            if (htmlEditor) htmlEditor.setValue(value);
            break;
        case 'css':
            if (cssEditor) cssEditor.setValue(value);
            break;
        case 'js':
            if (jsEditor) jsEditor.setValue(value);
            break;
    }
}

document.querySelectorAll('.btn_3').forEach(button => {
    button.addEventListener('click', () => {
        const lang = button.id.split('-')[0]; 
        
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`${lang}-tab`).classList.add('active');
        
        switch(lang) {
            case 'html':
                if (!htmlEditor) initEditor('html');
                break;
            case 'css':
                if (!cssEditor) initEditor('css');
                break;
            case 'js':
                if (!jsEditor) initEditor('js');
                break;
        }
        
        setTimeout(() => {
            switch(lang) {
                case 'html':
                    if (htmlEditor) htmlEditor.focus();
                    break;
                case 'css':
                    if (cssEditor) cssEditor.focus();
                    break;
                case 'js':
                    if (jsEditor) jsEditor.focus();
                    break;
            }
        }, 100);
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const htmlButton = document.getElementById('html-button');
    if (htmlButton) {
        console.log("Auto-clicking HTML button");
        htmlButton.click();
    }
});

window.getEditorValue = getEditorValue;
window.setEditorValue = setEditorValue;