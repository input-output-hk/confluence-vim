" based on
" http://brainacle.com/how-to-write-vim-plugins-with-python.html

" TODO deal with alternate encodings

if !has('python')
    echo "Error: Required vim compiled with +python"
    finish
endif

"augroup Confluence
"  au!
"  au BufReadCmd conf://* call OpenConfluencePage(expand("<amatch>"))
"  au BufWriteCmd conf://* call WriteConfluencePage(expand("<amatch>"))
"augroup END
