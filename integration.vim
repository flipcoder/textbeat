au BufNewFile,BufRead *.dc set ve=all
au BufNewFile,BufRead *.dc let b:dispatch = '~/bin/decadence ' . shellescape(expand('%:p'),1)
au BufNewFile,BufRead *.dc noremap <cr> :Dispatch! ~/bin/decadence -l <C-R>=shellescape(getline('.'),1)<cr><cr>
au BufNewFile,BufRead *.dc let &l:colorcolumn = join(range(14,100,16),',')
