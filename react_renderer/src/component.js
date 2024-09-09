import React, { useState } from 'react';
import { Button, Typography, Box, Grid, Paper, Divider } from '@mui/material';
import { Calculate as CalculatorIcon } from '@mui/icons-material';

const Calculator = () => {
  const [display, setDisplay] = useState('0');
  const [firstOperand, setFirstOperand] = useState(null);
  const [operator, setOperator] = useState(null);
  const [waitingForSecondOperand, setWaitingForSecondOperand] = useState(false);

  const inputDigit = (digit) => {
    if (waitingForSecondOperand) {
      setDisplay(String(digit));
      setWaitingForSecondOperand(false);
    } else {
      setDisplay(display === '0' ? String(digit) : display + digit);
    }
  };

  const inputDecimal = () => {
    if (waitingForSecondOperand) {
      setDisplay('0.');
      setWaitingForSecondOperand(false);
      return;
    }
    if (!display.includes('.')) {
      setDisplay(display + '.');
    }
  };

  const clear = () => {
    setDisplay('0');
    setFirstOperand(null);
    setOperator(null);
    setWaitingForSecondOperand(false);
  };

  const performOperation = (nextOperator) => {
    const inputValue = parseFloat(display);

    if (firstOperand === null) {
      setFirstOperand(inputValue);
    } else if (operator) {
      const result = calculate(firstOperand, inputValue, operator);
      setDisplay(String(result));
      setFirstOperand(result);
    }

    setWaitingForSecondOperand(true);
    setOperator(nextOperator);
  };

  const calculate = (firstOperand, secondOperand, operator) => {
    switch (operator) {
      case '+':
        return firstOperand + secondOperand;
      case '-':
        return firstOperand - secondOperand;
      case '*':
        return firstOperand * secondOperand;
      case '/':
        return firstOperand / secondOperand;
      case '^':
        return Math.pow(firstOperand, secondOperand);
      default:
        return secondOperand;
    }
  };

  const performSpecialOperation = (operation) => {
    const inputValue = parseFloat(display);
    let result;

    switch (operation) {
      case 'sin':
        result = Math.sin(inputValue);
        break;
      case 'cos':
        result = Math.cos(inputValue);
        break;
      case 'tan':
        result = Math.tan(inputValue);
        break;
      case 'log':
        result = Math.log10(inputValue);
        break;
      case 'ln':
        result = Math.log(inputValue);
        break;
      case '1/x':
        result = 1 / inputValue;
        break;
      case '√':
        result = Math.sqrt(inputValue);
        break;
      case '%':
        result = inputValue / 100;
        break;
      case 'π':
        result = Math.PI;
        break;
      default:
        return;
    }

    setDisplay(String(result));
    setFirstOperand(result);
    setWaitingForSecondOperand(true);
  };

  const buttons = [
    'sin', 'cos', 'tan', '7', '8', '9', '/',
    'log', 'ln', '1/x', '4', '5', '6', '*',
    '^', '√', '%', '1', '2', '3', '-',
    '(', ')', 'π', '0', '.', '=', '+'
  ];

  return (
    <Box 
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        p: 2,
        backgroundColor: '#f0f4f8',
        minHeight: '100vh',
      }}
    >
      <Typography variant="h4" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
        <CalculatorIcon />
        Advanced Calculator
      </Typography>
      <Paper 
        elevation={3}
        sx={{
          width: '100%',
          maxWidth: 300,
          p: 2,
          borderRadius: 2,
          backgroundColor: 'white',
        }}
      >
        <Paper 
          elevation={1}
          sx={{
            p: 1,
            mb: 1,
            backgroundColor: '#e3f2fd',
            borderRadius: 1,
            textAlign: 'right',
          }}
        >
          <Typography variant="h6">{display}</Typography>
        </Paper>
        <Button
          variant="contained"
          fullWidth
          onClick={clear}
          sx={{
            mb: 1,
            backgroundColor: '#ff5252',
            '&:hover': { backgroundColor: '#ff1744' },
          }}
        >
          Clear
        </Button>
        <Divider sx={{ my: 1 }} />
        <Grid container spacing={1}>
          {buttons.map((btn) => (
            <Grid item xs={3} key={btn}>
              <Button
                variant="contained"
                fullWidth
                onClick={() => {
                  if ('0123456789'.includes(btn)) {
                    inputDigit(parseInt(btn, 10));
                  } else if (btn === '.') {
                    inputDecimal();
                  } else if (['+', '-', '*', '/', '^'].includes(btn)) {
                    performOperation(btn);
                  } else if (btn === '=') {
                    performOperation(null);
                  } else {
                    performSpecialOperation(btn);
                  }
                }}
                sx={{
                  minWidth: 0,
                  p: 1,
                  backgroundColor: '#64b5f6',
                
                  color: 'white',
                  fontWeight: 'bold',
                }}
              >
                {btn}
              </Button>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Box>
  );
};

export default Calculator;