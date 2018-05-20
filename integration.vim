" virtual edit for better column editing
au BufNewFile,BufRead *.dec set ve=all

" play file
au BufNewFile,BufRead *.dec let b:dispatch = '~/bin/decadence ' . shellescape(expand('%:p'),1)

" play note with <cr> key - INSECURE
au BufNewFile,BufRead *.dec noremap <cr> :Dispatch! ~/bin/decadence -c <C-R>=shellescape(getline('.'),1)<cr><cr>
